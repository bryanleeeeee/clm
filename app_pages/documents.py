import streamlit as st
from clm.streamlit_support import state,api
data=state();st.title('Document centre');st.caption('Every upload stays connected to a client and a review decision.')
status=st.selectbox('Review status',['All','Pending review','Verified','Rejected'])
docs=[dict(d,client=c['name'],caseId=c['id']) for c in data['cases'] for d in c['documents'] if status=='All' or d['status']==status]
with st.container(horizontal=True):
    for kind in ['Pending review','Verified','Rejected']: st.metric(kind,sum(d['status']==kind for c in data['cases'] for d in c['documents']),border=True)
st.dataframe([{'Client':d['client'],'Document':d['name'],'Category':d['type'],'Status':d['status'],'Uploaded':d['uploadedAt']} for d in docs],hide_index=True)
if docs:
    uid=st.selectbox('Download a document',[d['id'] for d in docs],format_func=lambda uid:next(d['client']+' — '+d['name'] for d in docs if d['id']==uid))
    d=next(d for d in docs if d['id']==uid);content=api().request('/cases/'+d['caseId']+'/documents/'+d['id'],raw=True)
    st.download_button('Download selected file',content,file_name=d['name'])
st.info('Upload and review documents from the onboarding case, or use the Client demo role for self-service uploads.')
