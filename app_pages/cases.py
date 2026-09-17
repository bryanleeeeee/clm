import streamlit as st
from clm.streamlit_support import state,submit
from clm.streamlit_case import render_case
data=state();st.title('Onboarding workspace');st.caption('Every relationship. Every step. One connected case.')
with st.expander('Create a new onboarding',icon=':material/person_add:'):
    with st.form('new_case'):
        left,right=st.columns(2)
        name=left.text_input('Client / entity name');email=right.text_input('Email address')
        kind=left.selectbox('Client type',['Individual','Company','Family office']);risk=right.selectbox('Risk',['Low','Medium','High'])
        residency=left.text_input('Country of residence','Singapore');aum=right.number_input('Assets (SGD millions)',min_value=0.0,value=5.0)
        owner=left.selectbox('Relationship manager',['Sarah Chen','James Lim','David Koh']);pep=right.checkbox('Politically exposed person')
        if st.form_submit_button('Create onboarding',type='primary'):
            submit('/cases','POST',dict(name=name,email=email,type=kind,risk=risk,residency=residency,aum=aum,owner=owner,pep=pep),'Onboarding created')
search=st.text_input('Find a relationship',placeholder='Client name or case ID',icon=':material/search:')
filtered=[c for c in data['cases'] if search.lower() in (c['name']+' '+c['id']).lower()]
if not filtered: st.info('No cases match your search.');st.stop()
cid=st.selectbox('Open case',[c['id'] for c in filtered],format_func=lambda uid:next(c['name']+' · '+c['stage']+' · '+uid for c in filtered if c['id']==uid),key='selected_case')
render_case(next(c for c in filtered if c['id']==cid),data)
