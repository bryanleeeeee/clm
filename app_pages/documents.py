import streamlit as st
from clm.streamlit_support import state,api
from clm.presentation import header,open_case

data=state();header('Evidence & verification','Document centre','One document vault. A clear review status. Every file connected to its relationship.')
all_docs=[dict(d,client=c['name'],caseId=c['id']) for c in data['cases'] for d in c['documents']]
with st.container(horizontal=True):
    for kind,icon in [('Pending review','pending_actions'),('Verified','verified'),('Rejected','error_outline')]:
        st.metric(':material/'+icon+': '+kind,sum(d['status']==kind for d in all_docs),border=True)
with st.container(border=True):
    a,b=st.columns([2,1])
    search=a.text_input('Find evidence',placeholder='Client, document or category',icon=':material/search:')
    status=b.selectbox('Review status',['All','Pending review','Verified','Rejected'])
    docs=[d for d in all_docs if (status=='All' or d['status']==status) and search.lower() in (d['client']+' '+d['name']+' '+d['type']).lower()]
    st.caption(f'{len(docs)} documents · Select a row to download the file or open its review workspace.')
    selected=st.dataframe([{'Client':d['client'],'Document':d['name'],'Category':d['type'],'Status':d['status'],'Uploaded':d['uploadedAt'][:10]} for d in docs],hide_index=True,on_select='rerun',selection_mode='single-row',key='document_register',row_height=44)
    if selected.selection.rows and docs:
        d=docs[selected.selection.rows[0]]
        with st.container(horizontal=True):
            content=api().request('/cases/'+d['caseId']+'/documents/'+d['id'],raw=True)
            st.download_button('Download file',content,file_name=d['name'],icon=':material/download:')
            if st.button('Open review workspace',type='primary',icon=':material/arrow_forward:'): open_case(d['caseId'],'Documents')
    elif not docs: st.info('No documents match these filters.')
st.caption('To upload new evidence, open a relationship in Onboarding or preview the Client portal from the sidebar.')
