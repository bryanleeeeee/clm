import streamlit as st
from datetime import date
from clm.streamlit_support import state
from clm.presentation import header,journey,case_rows,evidence,due_label,open_case

data=state();cases=data['cases']
left,right=st.columns([4,1],vertical_alignment='center')
with left: header('Your relationship workspace',data['ui']['heading'],data['ui']['subtitle'])
with right:
    if st.button('New onboarding',type='primary',icon=':material/add:',width='stretch'):
        st.session_state['_create_case']=True;st.switch_page('app_pages/cases.py')
opened=[c for c in cases if c['stageKind'] not in ['active','closed']]
attention=sorted([c for c in opened if (date.fromisoformat(c['dueDate'])-date.today()).days<=3],key=lambda c:c['dueDate'])
metrics={'open':('Open lifecycle cases',len(opened),'work','Onboarding & periodic review'),'approval':('Awaiting approval',sum(c['stageKind']=='approval' for c in cases),'verified_user','Independent review pending'),'attention':('Needs attention',len(attention),'schedule','Overdue or due within 3 days'),'assets':('Relationship assets',f'S${sum(c["aum"] for c in cases):,.1f}M','account_balance','Indicative assets · SGD')}
if data['ui']['dashboardCards']:
    metric_columns=st.columns(len(data['ui']['dashboardCards']))
    for col,key in zip(metric_columns,data['ui']['dashboardCards']):
        label,value,icon,context=metrics[key]
        with col.container(border=True,gap='xsmall'):
            st.metric(':material/'+icon+': '+label,value)
            st.caption(context)
with st.container(border=True):
    st.subheader('Your client lifecycle')
    journey(data['workflow']['stages'],cases=cases)
left,right=st.columns([2,1],gap='large')
with left:
    title,action=st.columns([3,1],vertical_alignment='center')
    title.subheader('Relationships in progress')
    if action.button('View all',icon=':material/arrow_forward:',width='stretch'): st.session_state.pop('_open_case',None);st.switch_page('app_pages/cases.py')
    queue=st.segmented_control('Relationship queue',['All in progress','Awaiting approval','Needs attention'],default='All in progress',label_visibility='collapsed')
    visible=attention if queue=='Needs attention' else [c for c in opened if c['stageKind']=='approval'] if queue=='Awaiting approval' else opened
    case_rows(visible,'overview',limit=5)
    if len(visible)>5: st.caption(f'Showing 5 of {len(visible)} relationships · View all to search and filter')
with right:
    with st.container(border=True):
        st.subheader('Your priorities')
        st.caption('The nearest deadlines, in one place.')
        for c in attention[:3]:
            st.markdown('**'+c['name']+'**')
            st.caption(due_label(c)+' · '+c['stage'])
            if st.button('Review '+c['name'],key='priority_'+c['id'],icon=':material/arrow_forward:',width='stretch'): open_case(c['id'])
        if not attention: st.success('No urgent deadlines. You are up to date.')
    with st.container(border=True):
        st.subheader('Document readiness')
        counts=[evidence(c) for c in opened];verified=sum(x[0] for x in counts);total=sum(x[1] for x in counts)
        st.metric('Required evidence verified',f'{round(verified/max(1,total)*100)}%')
        st.progress(verified/max(1,total));st.caption(f'{verified} of {total} required categories verified')
        if st.button('Open document centre',icon=':material/folder_open:',width='stretch'): st.switch_page('app_pages/documents.py')
