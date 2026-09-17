"""Native Streamlit private banking workspace for Cloud and Cloudera."""
import streamlit as st
from clm.streamlit_support import api,state
from clm.defaults import ROLES
from clm.presentation import brand_logo
st.set_page_config(page_title='Aurelia | Synthetic CLM demo',page_icon=':material/account_balance:',layout='wide')
data=state()
st.logo(brand_logo(data['ui']['brand']),size='large')
st.warning('SYNTHETIC DATA — NOT REAL CLIENT DATA. Demonstration workspace only.',icon=':material/science:')
with st.sidebar:
    st.caption('SINGAPORE BOOKING CENTRE · SGD')
    with st.container(border=True):
        st.markdown(':material/account_circle: **Your workspace**')
        role=st.selectbox('Demo workspace role',ROLES,index=ROLES.index(data['session']['role']),key='demo_role')
        if role!=data['session']['role']:
            api().request('/session','POST',{'role':role,'clientId':data['session']['clientId']});st.rerun()
        if role!='Client':
            with st.expander('Client portal preview',icon=':material/visibility:'):
                ids=[c['id'] for c in data['cases']];labels={c['id']:c['name'] for c in data['cases']}
                selected=st.selectbox('Client portal identity',ids,index=ids.index(data['session']['clientId']) if data['session']['clientId'] in ids else 0,format_func=labels.get,key='portal_identity')
                if selected!=data['session']['clientId']:
                    api().request('/session','POST',{'role':role,'clientId':selected});st.rerun()
                st.caption('Select a relationship, then switch your role to Client.')
    st.caption('Demo role switching · No production authentication')
if '_notice' in st.session_state: st.success(st.session_state.pop('_notice'))
if role=='Client':
    pages=[st.Page('app_pages/client.py',title='My onboarding',icon=':material/person:')]
else:
    pages=[st.Page('app_pages/overview.py',title='Overview',icon=':material/dashboard:'),st.Page('app_pages/cases.py',title='Onboarding',icon=':material/work:'),st.Page('app_pages/documents.py',title='Document centre',icon=':material/folder:'),st.Page('app_pages/workflows.py',title='Workflows',icon=':material/account_tree:'),st.Page('app_pages/policies.py',title='Rules & policies',icon=':material/policy:'),st.Page('app_pages/reports.py',title='Reports & insights',icon=':material/analytics:'),st.Page('app_pages/settings.py',title='UI & settings',icon=':material/tune:')]
    visibility=data['ui']['navigation']
    pages=[p for p in pages if p.title in visibility or p.title=='UI & settings']
    pages={'Workspace':[p for p in pages if p.title in ['Overview','Onboarding','Document centre','Reports & insights']], 'Design & governance':[p for p in pages if p.title in ['Workflows','Rules & policies','UI & settings']]}
st.navigation(pages).run()
st.caption('Aurelia · Synthetic demonstration · Singapore · External banking services not connected')
