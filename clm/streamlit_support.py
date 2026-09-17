"""Per-session in-process WSGI gateway; Streamlit needs no second HTTP server."""
import os
import streamlit as st
from werkzeug.test import Client
from werkzeug.wrappers import Response
from .web import create_app

@st.cache_resource
def flask_resource(data_dir):
    return create_app({'DATA_DIR':data_dir}) if data_dir else create_app()

class LocalAPI:
    def __init__(self, app):
        self.client=Client(app,Response,use_cookies=True)
    def request(self,path,method='GET',data=None,raw=False):
        response=self.client.open('/api'+path,method=method,json=data)
        if response.status_code>=400:
            result=response.get_json(silent=True) or {}
            raise ValueError(result.get('error',f'Request failed: {response.status_code}'))
        return response.data if raw else response.get_json()

def api():
    if '_api' not in st.session_state:
        st.session_state['_api']=LocalAPI(flask_resource(os.environ.get('DATA_DIR')))
    return st.session_state['_api']

def state(): return api().request('/state')

def submit(path,method,data,message='Saved'):
    try:
        api().request(path,method,data)
        st.session_state['_notice']=message
        st.rerun()
    except ValueError as e: st.error(str(e))

def rows(value):
    return value.to_dict('records') if hasattr(value,'to_dict') else value

def condition_editor(group, prefix, data):
    from .defaults import FIELDS
    import pandas as pd
    options=list(FIELDS)+['custom.'+f['key'] for f in data['ui']['customFields']]
    matching=st.selectbox('Match conditions',['all','any'],index=['all','any'].index(group.get('match','all')),format_func=lambda x:'All conditions (AND)' if x=='all' else 'Any condition (OR)',key=prefix+'_match')
    st.caption('No conditions means always. For “in”, separate choices with commas. PEP uses true / false.')
    value=st.data_editor(pd.DataFrame([dict(field=x['field'],op=x['op'],value=str(x['value']).lower() if isinstance(x['value'],bool) else str(x['value'])) for x in group.get('items',[])],columns=['field','op','value']),num_rows='dynamic',hide_index=True,column_config={'field':st.column_config.SelectboxColumn('Client field',options=options,required=True),'op':st.column_config.SelectboxColumn('Comparison',options=['eq','ne','gt','gte','lt','lte','in','contains'],required=True),'value':st.column_config.TextColumn('Compare with',required=True)},key=prefix+'_conditions')
    return dict(match=matching,items=[dict(field=r.get('field'),op=r.get('op'),value=r.get('value','')) for r in rows(value)])

def custom_inputs(c,data,client=False):
    result={}
    for f in data['ui']['customFields']:
        value=c.get('customFields',{}).get(f['key'])
        disabled=not c.get('editable',True) or (client and not f['clientEditable'])
        label=f['label']+(' *' if f['key'] in c.get('requiredFields',[]) else '')
        kw=dict(key=c['id']+'_custom_'+f['key'],disabled=disabled)
        if f['type']=='checkbox': value=st.checkbox(label,value=bool(value),**kw)
        elif f['type']=='number': value=st.number_input(label,value=float(value) if value not in [None,''] else 0.0,**kw)
        elif f['type']=='textarea': value=st.text_area(label,value=value or '',**kw)
        elif f['type']=='select':
            options=['']+f['options'];value=st.selectbox(label,options,index=options.index(value) if value in options else 0,**kw)
        elif f['type']=='date':
            from datetime import date
            d=st.date_input(label,value=date.fromisoformat(value) if value else None,**kw);value=d.isoformat() if d else ''
        else: value=st.text_input(label,value=value or '',**kw)
        if not disabled: result[f['key']]=value
    return result
