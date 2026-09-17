from clm.presentation import header
import json
from copy import deepcopy
from uuid import uuid4
import streamlit as st
from clm.streamlit_support import state,submit
from clm.defaults import NAV
data=state();ui=deepcopy(data['ui']);header('Your operating model','UI & workspace settings','Configure your interface, onboarding forms and operating model. Operations can save changes.')
section=st.segmented_control('Settings section',['Appearance & layout','Form builder','Workspace'],default='Appearance & layout')
if section=='Appearance & layout':
    with st.form('ui_settings'):
        brand=st.text_input('Brand name',ui['brand']);heading=st.text_input('Dashboard heading',ui['heading']);subtitle=st.text_input('Dashboard subtitle',ui['subtitle'])
        a,b=st.columns(2);accent=a.color_picker('Chart / Flask accent colour',ui['accent']);density=b.selectbox('Table density',['comfortable','compact'],index=['comfortable','compact'].index(ui['density']))
        navigation=st.multiselect('Visible workspace sections',NAV,default=ui['navigation'])
        cards=st.multiselect('Dashboard cards',['open','approval','attention','assets'],default=ui['dashboardCards'],format_func={'open':'Open lifecycle cases','approval':'Awaiting approval','attention':'Needs attention','assets':'Relationship assets'}.get)
        st.caption('Core workflow and configuration sections remain available. Streamlit widget colours use the theme file below; chart colours update immediately.')
        if st.form_submit_button('Save appearance',type='primary'):
            ui.update(brand=brand,heading=heading,subtitle=subtitle,accent=accent,density=density,navigation=navigation,dashboardCards=cards)
            submit('/ui','PUT',dict(ui=ui,revision=data['revision']),'UI configuration saved')
    st.download_button('Download matching Streamlit theme',f'[theme]\nbase = "light"\nprimaryColor = "{ui["accent"]}"\nbackgroundColor = "#ffffff"\nsecondaryBackgroundColor = "#f3f7fc"\ntextColor = "#233c5d"\nborderColor = "#e0e8f2"\n',file_name='config.toml',mime='text/plain')
    st.caption('To change all Streamlit widget colours, replace .streamlit/config.toml with the downloaded theme and restart the application.')
elif section=='Form builder':
    st.info('Fields appear on staff and client onboarding profiles. Required fields become approval gates. Policies and workflow conditions can reference these fields.')
    for i,f in enumerate(ui['customFields']):
        with st.container(border=True):
            st.markdown(f'**{i+1}. {f["label"]}**');st.caption(f'{f["key"]} · {f["type"]} · '+('Required' if f['required'] else 'Optional')+' · '+('Client editable' if f['clientEditable'] else 'Staff only'))
            with st.container(horizontal=True):
                if st.button('Move up',key='up_'+f['key'],disabled=i==0):
                    ui['customFields'][i-1],ui['customFields'][i]=ui['customFields'][i],ui['customFields'][i-1];submit('/ui','PUT',dict(ui=ui,revision=data['revision']),'Field reordered')
                if st.button('Move down',key='down_'+f['key'],disabled=i==len(ui['customFields'])-1):
                    ui['customFields'][i+1],ui['customFields'][i]=ui['customFields'][i],ui['customFields'][i+1];submit('/ui','PUT',dict(ui=ui,revision=data['revision']),'Field reordered')
    selected=st.selectbox('Field to configure',['new']+[f['key'] for f in ui['customFields']],format_func=lambda key:'＋ Add field' if key=='new' else next(f['label'] for f in ui['customFields'] if f['key']==key))
    f=next((f for f in ui['customFields'] if f['key']==selected),dict(key='',label='',type='text',options=[],required=False,clientEditable=True))
    with st.form('field_form_'+selected):
        key=st.text_input('Stable field key',f['key'],disabled=selected!='new',placeholder='e.g. investment_objective')
        label=st.text_input('Field label',f['label']);kind=st.selectbox('Input type',['text','textarea','number','date','select','checkbox'],index=['text','textarea','number','date','select','checkbox'].index(f['type']))
        options=st.text_area('Choices for select fields — one per line','\n'.join(f['options']))
        required=st.checkbox('Required before approval',f['required']);client_editable=st.checkbox('Client can edit this field',f['clientEditable'])
        if st.form_submit_button('Save form field',type='primary'):
            updated=dict(key=key,label=label,type=kind,options=[x.strip() for x in options.splitlines() if x.strip()],required=required,clientEditable=client_editable)
            ui['customFields']=[updated if x['key']==selected else x for x in ui['customFields']]
            if selected=='new': ui['customFields'].append(updated)
            submit('/ui','PUT',dict(ui=ui,revision=data['revision']),'Form field saved')
    if selected!='new':
        confirm=st.checkbox('Remove this field from the form',key='remove_field_confirm')
        st.caption('Removal is blocked if a policy or published workflow still references the field. Previously saved values remain in case history/storage.')
        if st.button('Remove field',disabled=not confirm):
            ui['customFields']=[x for x in ui['customFields'] if x['key']!=selected];submit('/ui','PUT',dict(ui=ui,revision=data['revision']),'Form field removed')
else:
    with st.form('workspace_settings'):
        bank=st.text_input('Institution name',data['settings']['bankName']);days=st.number_input('Initial onboarding target (calendar days)',1,90,data['settings']['slaDays'])
        st.caption('Singapore booking centre · SGD reporting. Individual stage targets are set in the workflow designer.')
        if st.form_submit_button('Save workspace',type='primary'): submit('/settings','PUT',dict(bankName=bank,slaDays=days),'Workspace settings saved')
    st.subheader('Integration boundaries')
    st.dataframe([{'Service':n,'Status':'Not connected — demo only'} for n in ['Enterprise identity / MFA','Sanctions / PEP screening','Electronic signatures','Core banking','Malware scanning / secure storage']],hide_index=True)
