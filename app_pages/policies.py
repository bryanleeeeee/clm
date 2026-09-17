from copy import deepcopy
from uuid import uuid4
import streamlit as st
from clm.streamlit_support import state,submit,condition_editor
data=state();st.title('Rules & policies');st.caption('When a client matches these conditions, collect the right evidence. No code required.')
st.info('Base account opening, identity, address and tax forms always apply. Conditional policies add documents or required form fields. Compliance can save changes.')
with st.container(horizontal=True):
    for r in data['rules']:
        with st.container(border=True,width=270):
            st.badge('Enabled' if r['enabled'] else 'Disabled',color='green' if r['enabled'] else 'gray')
            st.markdown('**'+r['name']+'**');st.caption(r['description']);st.caption(f'{len(r["conditions"]["items"])} conditions · match {r["conditions"]["match"]}')
            for d in r['documents']: st.write(':material/description: '+d)
options=['new']+[r['id'] for r in data['rules']]
selected=st.selectbox('Policy to edit',options,format_func=lambda uid:'＋ Create policy' if uid=='new' else next(r['name'] for r in data['rules'] if r['id']==uid))
r=next((deepcopy(r) for r in data['rules'] if r['id']==selected),dict(id='rule-'+str(uuid4()),name='',enabled=True,description='',conditions={'match':'all','items':[]},documents=[],requiredFields=[]))
with st.form('policy_'+selected):
    name=st.text_input('Policy name',r['name']);description=st.text_area('Purpose / guidance',r['description']);enabled=st.checkbox('Enable this policy',r['enabled'])
    st.subheader('When these conditions match')
    conditions=condition_editor(r['conditions'],'policy_'+selected,data)
    st.subheader('Require this information')
    docs=st.text_area('Required documents — one category per line','\n'.join(r['documents']),placeholder='Source of wealth evidence\nInvestment suitability questionnaire')
    fields=st.multiselect('Additional required form fields',[f['key'] for f in data['ui']['customFields']],default=r.get('requiredFields',[]),format_func=lambda key:next(f['label'] for f in data['ui']['customFields'] if f['key']==key))
    if st.form_submit_button('Save policy',type='primary'):
        replacement=dict(id=r['id'],name=name,description=description,enabled=enabled,conditions=conditions,documents=[d.strip() for d in docs.splitlines() if d.strip()],requiredFields=fields)
        rules=[replacement if x['id']==selected else x for x in data['rules']]
        if selected=='new': rules.append(replacement)
        submit('/rules','PUT',dict(rules=rules,revision=data['revision']),'Policy saved; requirements recalculated')
st.subheader('Live policy impact')
st.dataframe([{'Client':c['name'],'Risk':c['risk'],'Required documents':len(c['requiredDocuments']),'Extra required fields':len(c['requiredFields']),'Open requirements':len(c['blockers'])} for c in data['cases']],hide_index=True)
