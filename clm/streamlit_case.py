"""Reusable case interface shared by staff and client pages."""
import base64
import streamlit as st
from .streamlit_support import api,submit,custom_inputs
from .defaults import CHECKS

def render_case(c,data,client=False):
    prefix='/cases/'+c['id']
    with st.container(border=True):
        st.subheader(c['name'])
        with st.container(horizontal=True):
            st.badge(c['stage'],color='blue');st.badge(c['risk']+' risk',color={'Low':'green','Medium':'orange','High':'red'}[c['risk']]);st.badge(f'Workflow v{c["workflowVersion"]}',color='gray')
        st.caption(f'{c["id"]} · {c["owner"]} · Target {c["dueDate"]}')
    section=st.segmented_control('Case section',['Overview','Profile','Documents'] if client else ['Overview','Profile','Documents','Due diligence','Activity'],default='Overview',key=c['id']+'_section')
    if section=='Overview':
        total=len(c['requiredDocuments']);verified=sum(any(d['type']==t and d['status']=='Verified' for d in c['documents']) for t in c['requiredDocuments'])
        st.progress(verified/max(1,total),text=f'{verified} of {total} required document categories verified')
        if c['blockers']:
            st.markdown('**Your next steps**' if client else '**Outstanding evidence and controls**')
            for issue in c['blockers']: st.write(':material/pending: '+issue)
        else: st.success('All current policy requirements are satisfied.')
        if not client:
            with st.form(c['id']+'_transition'):
                actions=c['availableActions']
                if actions:
                    route=st.selectbox('Next action',[a['id'] for a in actions],format_func=lambda uid:next(a['label']+' → '+a['target'] for a in actions if a['id']==uid))
                    note=st.text_area('Decision note',help='A reason is required for remediation or closure.')
                    if st.form_submit_button('Move case forward',type='primary'):
                        submit(prefix+'/transition','POST',dict(action=route,note=note),'Case moved to the next stage')
                else: st.info('No available routes at this stage. The case is retained for reference.')
    elif section=='Profile':
        with st.form(c['id']+'_profile'):
            left,right=st.columns(2)
            email=left.text_input('Email',c['email'],disabled=not c['editable']);phone=right.text_input('Phone',c['phone'],disabled=not c['editable'])
            residency=left.text_input('Country of residence',c['residency'],disabled=not c['editable']);tax=right.text_input('Tax residency',c['taxResidency'],disabled=not c['editable'])
            wealth=st.text_area('Source of wealth',c['sourceOfWealth'],disabled=not c['editable'])
            values=dict(email=email,phone=phone,residency=residency,taxResidency=tax,sourceOfWealth=wealth)
            if not client:
                values['risk']=st.selectbox('Risk classification',['Low','Medium','High'],index=['Low','Medium','High'].index(c['risk']),disabled=not c['editable'])
                values['owner']=st.text_input('Relationship manager',c['owner'],disabled=not c['editable']);values['pep']=st.checkbox('Politically exposed person',c['pep'],disabled=not c['editable'])
            if data['ui']['customFields']: st.markdown('**Additional onboarding information**')
            values['customFields']=custom_inputs(c,data,client)
            values['consent']=st.checkbox('I confirm the synthetic information is accurate for this demonstration.' if client else 'Client declaration obtained and recorded',c['consent'],disabled=not c['editable'])
            st.caption('Saving a changed profile resets due diligence checks for review.')
            if st.form_submit_button('Save client details',type='primary',disabled=not c['editable']): submit(prefix,'PATCH',values,'Client details saved')
    elif section=='Documents':
        if c['editable']:
            with st.form(c['id']+'_upload',clear_on_submit=True):
                category=st.selectbox('Document category',c['requiredDocuments'])
                uploaded=st.file_uploader('Upload synthetic evidence',type=['pdf','png','jpg','jpeg'],max_upload_size=10)
                if st.form_submit_button('Upload document',type='primary'):
                    if uploaded: submit(prefix+'/documents','POST',dict(name=uploaded.name,type=category,content=base64.b64encode(uploaded.getvalue()).decode()),'Document uploaded for review')
                    else: st.error('Choose a file first.')
        for category in c['requiredDocuments']:
            with st.container(border=True):
                st.markdown('**'+category+'**')
                docs=[d for d in c['documents'] if d['type']==category]
                if not docs: st.caption('Awaiting upload')
                for d in docs:
                    st.write(d['name']);st.badge(d['status'],color='green' if d['status']=='Verified' else 'orange')
                    if d.get('reviewNote'): st.caption('Review: '+d['reviewNote'])
                    content=api().request(prefix+'/documents/'+d['id'],raw=True)
                    st.download_button('Download',content,file_name=d['name'],key='download_'+d['id'])
                    if not client and c['editable']:
                        with st.expander('Record document review',expanded=False):
                            with st.form('review_'+d['id']):
                                status=st.selectbox('Outcome',['Verified','Rejected']);note=st.text_area('Review evidence / reason')
                                if st.form_submit_button('Save review'): submit(prefix+'/documents/'+d['id']+'/review','POST',dict(status=status,note=note),'Document review recorded')
    elif section=='Due diligence':
        st.info('Human review attestations only. No external sanctions or identity service is connected.')
        for key,label in CHECKS.items():
            with st.expander(label+(' — complete' if c['kyc'][key] else ' — pending'),expanded=not c['kyc'][key]):
                with st.form(c['id']+'_kyc_'+key):
                    note=st.text_area('Evidence reference and outcome')
                    if st.form_submit_button('Reopen check' if c['kyc'][key] else 'Complete check',disabled=not c['canReview']): submit(prefix+'/kyc','PUT',dict(check=key,checked=not c['kyc'][key],note=note),'Due diligence recorded')
    elif section=='Activity':
        with st.form(c['id']+'_note'):
            note=st.text_area('Add a case note')
            if st.form_submit_button('Save note',disabled=c['stageKind']=='closed'): submit(prefix+'/notes','POST',dict(note=note),'Note recorded')
        st.dataframe([{'Time':a['at'],'Actor':a['actor'],'Action':a['action'],'Note':a.get('note','')} for a in c['activity']],hide_index=True)
