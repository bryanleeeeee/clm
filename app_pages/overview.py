import streamlit as st
from clm.streamlit_support import state
from datetime import date
data=state();cases=data['cases']
st.caption('YOUR WORKSPACE, AT A GLANCE')
st.title(data['ui']['heading']);st.write(data['ui']['subtitle'])
opened=[c for c in cases if c['stageKind'] not in ['active','closed']]
metrics={'open':('Open lifecycle cases',len(opened)),'approval':('Awaiting approval',sum(c['stageKind']=='approval' for c in cases)),'attention':('Needs attention',sum((date.fromisoformat(c['dueDate'])-date.today()).days<=3 for c in opened)),'assets':('Indicative relationship assets',f'S${sum(c["aum"] for c in cases):,.1f}M')}
with st.container(horizontal=True):
    for key in data['ui']['dashboardCards']:
        label,value=metrics[key];st.metric(label,value,border=True)
a,b=st.columns([1.7,1])
with a,st.container(border=True):
    st.subheader('Your client lifecycle')
    counts=[{'Stage':s,'Cases':sum(c['stage']==s for c in cases)} for s in data['stages']]
    st.bar_chart(counts,x='Stage',y='Cases',color=data['ui']['accent'],horizontal=True)
with b,st.container(border=True):
    st.subheader('Document readiness')
    total=sum(len(c['requiredDocuments']) for c in opened)
    verified=sum(sum(any(d['type']==t and d['status']=='Verified' for d in c['documents']) for t in c['requiredDocuments']) for c in opened)
    st.metric('Required categories verified',f'{round(verified/max(1,total)*100)}%')
    st.progress(verified/max(1,total));st.caption(f'{verified} of {total} required categories verified')
    st.info('Next step: open a case, collect its required evidence, then move through the configured review routes.')
    if st.button('Open onboarding workspace',type='primary',icon=':material/arrow_forward:'): st.switch_page('app_pages/cases.py')
st.subheader('Relationships in progress')
st.dataframe([{'Client':c['name'],'Case':c['id'],'Stage':c['stage'],'Risk':c['risk'],'Manager':c['owner'],'Assets (SGD M)':c['aum'],'Target date':c['dueDate'],'Workflow':f'v{c["workflowVersion"]}'} for c in opened],hide_index=True,row_height=30 if data['ui']['density']=='compact' else 42)
