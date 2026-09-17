import streamlit as st
from clm.streamlit_support import state,api
from clm.streamlit_case import render_case
from clm.presentation import header,case_rows,evidence,due_label,open_case

def close_create(): st.session_state['_creating_case']=False

@st.dialog('Start a new relationship',width='large',on_dismiss=close_create)
def new_onboarding():
    st.caption('Create a synthetic case. The published workflow and policies take care of the next steps.')
    with st.form('new_case'):
        left,right=st.columns(2)
        name=left.text_input('Client / entity name');email=right.text_input('Email address')
        kind=left.selectbox('Client type',['Individual','Company','Family office']);risk=right.selectbox('Risk',['Low','Medium','High'])
        residency=left.text_input('Country of residence','Singapore');aum=right.number_input('Assets (SGD millions)',min_value=0.0,value=5.0)
        owner=left.selectbox('Relationship manager',['Sarah Chen','James Lim','David Koh']);pep=right.checkbox('Politically exposed person')
        if st.form_submit_button('Create onboarding',type='primary',icon=':material/add:'):
            try:
                result=api().request('/cases','POST',dict(name=name,email=email,type=kind,risk=risk,residency=residency,aum=aum,owner=owner,pep=pep))
                st.session_state['_creating_case']=False;st.session_state['_open_case']=result['id'];st.session_state['_notice']='Your onboarding case is ready.';st.rerun()
            except ValueError as e: st.error(str(e))

data=state()
opened_id=st.session_state.get('_open_case')
selected=next((c for c in data['cases'] if c['id']==opened_id),None)
if selected:
    with st.container(horizontal=True):
        if st.button('All relationships',icon=':material/arrow_back:'):
            st.session_state.pop('_open_case',None);st.rerun()
        with st.popover('Switch relationship',icon=':material/swap_horiz:'):
            target=st.selectbox('Open case',[c['id'] for c in data['cases']],format_func=lambda uid:next(c['name'] for c in data['cases'] if c['id']==uid),index=[c['id'] for c in data['cases']].index(selected['id']))
            if st.button('Open selected relationship'): st.session_state['_open_case']=target;st.rerun()
    render_case(selected,data)
else:
    a,b=st.columns([4,1],vertical_alignment='center')
    with a: header('Client lifecycle management','Onboarding workspace','From first conversation to an enduring relationship. Keep every next step in view.')
    if b.button('New onboarding',type='primary',icon=':material/add:',width='stretch'): st.session_state['_creating_case']=True
    with st.container(horizontal=True):
        st.badge(f'{len(data["cases"])} relationships',color='blue')
        st.badge(f'{sum(c["stageKind"]=="approval" for c in data["cases"])} awaiting approval',color='orange')
    with st.container(border=True):
        a,b,c=st.columns([2,1,1],vertical_alignment='bottom')
        search=a.text_input('Find a relationship',placeholder='Search client name or case ID',icon=':material/search:')
        stage=b.selectbox('Lifecycle stage',['All stages']+data['stages'])
        risk=c.selectbox('Risk level',['All risks','Low','Medium','High'])
        layout=st.segmented_control('Workspace view',['Relationship list','Pipeline board'],default='Relationship list',label_visibility='collapsed')
    filtered=[c for c in data['cases'] if search.lower() in (c['name']+' '+c['id']).lower() and (stage=='All stages' or c['stage']==stage) and (risk=='All risks' or c['risk']==risk)]
    st.caption(f'{len(filtered)} relationships · Select Open case to view the profile, documents and next action.')
    if layout=='Pipeline board':
        names=[s for s in data['stages'] if stage=='All stages' or s==stage]
        with st.container(horizontal=True,wrap=False):
            for name in names:
                items=[c for c in filtered if c['stage']==name]
                with st.container(width=265):
                    st.markdown('**'+name+'**');st.caption(f'{len(items)} relationships')
                    for c in items:
                        with st.container(border=True):
                            st.markdown('**'+c['name']+'**');st.caption(c['id'])
                            st.badge(c['risk']+' risk',color={'Low':'green','Medium':'orange','High':'red'}[c['risk']])
                            verified,total=evidence(c);st.progress(verified/max(1,total),text=f'{verified}/{total} evidence verified')
                            st.caption(c['owner']+' · '+due_label(c))
                            if st.button('Open case',key='board_'+c['id'],icon=':material/arrow_forward:',width='stretch'): open_case(c['id'])
                    if not items: st.caption('No cases at this stage')
    else: case_rows(filtered,'directory')
if st.session_state.pop('_create_case',False): st.session_state['_creating_case']=True
if st.session_state.get('_creating_case'): new_onboarding()
