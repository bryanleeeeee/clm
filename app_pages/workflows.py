import json
from copy import deepcopy
from uuid import uuid4
import streamlit as st
from clm.streamlit_support import state,api,condition_editor
from clm.defaults import STAFF,GUARDS,KINDS
from clm.domain import mandatory_guards

data=state();st.title('Workflow studio');st.caption('Design the journey. Make the decisions clear. Test before publishing.')
if '_workflow_edit' not in st.session_state:
    st.session_state['_workflow_edit']=deepcopy(data['workflowDraft']);st.session_state['_workflow_revision']=data['draftRevision'];st.session_state['_workflow_dirty']=False
w=st.session_state['_workflow_edit']

def changed():
    st.session_state['_workflow_dirty']=True;st.rerun()

def save_draft():
    try:
        api().request('/workflow/draft','PUT',{'workflow':w,'draftRevision':st.session_state['_workflow_revision']})
        st.session_state['_workflow_revision']=state()['draftRevision'];st.session_state['_workflow_dirty']=False
        st.session_state['_notice']='Draft saved. Live cases are unchanged.';st.rerun()
    except ValueError as e: st.error(str(e))

with st.container(horizontal=True):
    st.badge(f'Published v{data["workflow"]["version"]}',color='green')
    st.badge('Unsaved draft changes' if st.session_state['_workflow_dirty'] else 'Draft saved',color='orange' if st.session_state['_workflow_dirty'] else 'blue')
    if st.button('Save draft',type='primary',icon=':material/save:'): save_draft()
    if st.button('Reload saved draft',icon=':material/refresh:'):
        st.session_state.pop('_workflow_edit');st.rerun()
mode=st.segmented_control('Workflow workspace',['Design journey','Configure routes','Test & publish','Version history'],default='Design journey',key='workflow_workspace')
if mode=='Design journey':
    with st.form('workflow_identity'):
        name=st.text_input('Workflow name',w['name'])
        names=[s['name'] for s in w['stages']]
        start=st.selectbox('New cases start at',names,index=names.index(w['startStage']) if w['startStage'] in names else 0)
        if st.form_submit_button('Apply workflow details'): w.update(name=name,startStage=start);changed()
    st.subheader('Your journey at a glance')
    with st.container(horizontal=True):
        for i,s in enumerate(w['stages']):
            with st.container(border=True,width=180):
                st.caption(f'STEP {i+1:02d} · {s["kind"].upper()}')
                st.markdown('**'+s['name']+'**');st.caption(s['owner']);st.caption(f'{s["slaDays"]} days · '+('Editable' if s['editable'] else 'Locked'))
    st.caption('The cards show display order; routes below determine which steps each client takes.')
    left,right=st.columns([1.2,1])
    with left,st.container(border=True):
        st.subheader('Edit a stage')
        selected=st.selectbox('Stage',names,key='edit_stage')
        idx=names.index(selected);s=w['stages'][idx]
        with st.form('edit_stage_form_'+selected):
            label=st.text_input('Stage name',s['name']);kind=st.selectbox('Stage purpose',KINDS,index=KINDS.index(s['kind']))
            owner=st.selectbox('Responsible team',STAFF,index=STAFF.index(s['owner']))
            days=st.number_input('Target time (calendar days)',1,365,s['slaDays'])
            editable=st.checkbox('Allow profile and document changes',s['editable'])
            description=st.text_area('Guidance for the team',s['description'])
            if st.form_submit_button('Apply stage changes'):
                if not label.strip() or (label!=selected and label in names): st.error('Use a unique, non-empty stage name.')
                else:
                    w['stages'][idx]=dict(name=label.strip(),kind=kind,owner=owner,slaDays=days,editable=editable if kind not in ['approval','active','closed'] else False,description=description)
                    for r in w['transitions']:
                        if r['source']==selected: r['source']=label.strip()
                        if r['target']==selected: r['target']=label.strip()
                    if w['startStage']==selected: w['startStage']=label.strip()
                    changed()
        with st.container(horizontal=True):
            if st.button('Move earlier',disabled=idx==0): w['stages'][idx-1],w['stages'][idx]=w['stages'][idx],w['stages'][idx-1];changed()
            if st.button('Move later',disabled=idx==len(names)-1): w['stages'][idx+1],w['stages'][idx]=w['stages'][idx],w['stages'][idx+1];changed()
        with st.expander('Remove this stage'):
            st.caption('Connected routes will also be removed. You must reconnect the journey before publishing.')
            confirm=st.checkbox('Remove the stage and its routes',key='delete_confirm_'+selected)
            if st.button('Remove stage',disabled=not confirm):
                w['stages'].pop(idx);w['transitions']=[r for r in w['transitions'] if selected not in [r['source'],r['target']]];changed()
    with right,st.container(border=True):
        st.subheader('Add a step to the journey')
        st.write('Insert a stage into an existing route. The designer reconnects both sides for you.')
        with st.form('insert_stage'):
            label=st.text_input('New stage name',placeholder='e.g. Investment suitability')
            route_ids=[r['id'] for r in w['transitions']]
            rid=st.selectbox('Insert into route',route_ids,format_func=lambda uid:next(r['source']+' → '+r['target'] for r in w['transitions'] if r['id']==uid))
            owner=st.selectbox('New stage owner',STAFF);days=st.number_input('Stage target (days)',1,365,3)
            if st.form_submit_button('Insert stage',type='primary',icon=':material/add:'):
                if not label.strip() or label.strip() in names: st.error('Enter a new, unique stage name.')
                else:
                    label=label.strip();r=next(r for r in w['transitions'] if r['id']==rid);old=deepcopy(r)
                    index=next(i for i,s in enumerate(w['stages']) if s['name']==r['source'])
                    w['stages'].insert(index+1,dict(name=label,kind='custom',owner=owner,slaDays=days,editable=True,description='Complete the additional review before continuing.'))
                    r['target']=label;r['label']='Continue to '+label
                    old.update(id='route-'+str(uuid4()),source=label,resetChecks=False)
                    w['transitions'].append(old);changed()
    st.subheader('Connected routes')
    st.dataframe([{'From':r['source'],'Action':r['label'],'To':r['target'],'Roles':', '.join(r['roles']),'Checks':', '.join(GUARDS[g] for g in r['guards'])} for r in w['transitions']],hide_index=True)
elif mode=='Configure routes':
    st.info('Routes can branch by risk, client type, assets, geography or custom form fields. All/any conditions support AND/OR matching. Each eligible action appears on the case.')
    options=['new']+[r['id'] for r in w['transitions']]
    rid=st.selectbox('Route to configure',options,format_func=lambda uid:'＋ Add a new route' if uid=='new' else next(r['source']+' → '+r['target']+' · '+r['label'] for r in w['transitions'] if r['id']==uid))
    route=next((deepcopy(r) for r in w['transitions'] if r['id']==rid),dict(id='route-'+str(uuid4()),label='Continue',source=w['stages'][0]['name'],target=w['stages'][1]['name'],roles=['Relationship manager'],guards=[],conditions={'match':'all','items':[]},resetChecks=False))
    names=[s['name'] for s in w['stages']];byname={s['name']:s for s in w['stages']}
    a,b=st.columns(2)
    source=a.selectbox('From stage',names,index=names.index(route['source']),key=rid+'_source')
    target=b.selectbox('To stage',names,index=names.index(route['target']),key=rid+'_target')
    required=mandatory_guards(byname[target],byname[source])
    with st.form('route_form_'+rid):
        label=st.text_input('Action shown to the user',route['label'])
        roles=st.multiselect('Who can take this action?',STAFF,default=route['roles'])
        guards=st.multiselect('Required checks',list(GUARDS),default=list(dict.fromkeys(route['guards']+required)),format_func=GUARDS.get)
        if required: st.caption('Mandatory for this destination: '+', '.join(GUARDS[g] for g in required))
        reset=st.checkbox('Reset due diligence when this route is taken',route['resetChecks'])
        conditions=condition_editor(route['conditions'],rid,data)
        if st.form_submit_button('Apply route to draft',type='primary'):
            replacement=dict(id=route['id'],label=label,source=source,target=target,roles=roles,guards=list(dict.fromkeys(guards+required)),conditions=conditions,resetChecks=reset)
            w['transitions']=[replacement if r['id']==rid else r for r in w['transitions']]
            if rid=='new': w['transitions'].append(replacement)
            changed()
    if rid!='new':
        if st.button('Remove route',icon=':material/delete:'): w['transitions']=[r for r in w['transitions'] if r['id']!=rid];changed()
elif mode=='Test & publish':
    st.subheader('Try a case before you publish')
    st.caption('The simulator uses your draft and never changes the case.')
    cases={c['id']:c for c in data['cases']}
    cid=st.selectbox('Test case',list(cases),format_func=lambda uid:cases[uid]['name'])
    with st.form('simulate_workflow'):
        left,right=st.columns(2)
        stage=left.selectbox('Start simulation at',[s['name'] for s in w['stages']]);role=right.selectbox('Acting role',STAFF,index=1)
        risk=left.selectbox('Scenario risk',['Low','Medium','High'],index=['Low','Medium','High'].index(cases[cid]['risk']))
        aum=right.number_input('Scenario assets (SGD millions)',value=float(cases[cid]['aum']),min_value=0.0)
        pep=left.checkbox('Scenario PEP',cases[cid]['pep']);note=right.text_input('Decision reason for simulation','Synthetic simulation decision')
        if st.form_submit_button('Run simulation',type='primary',icon=':material/play_arrow:'):
            try:
                result=api().request('/workflow/simulate','POST',dict(workflow=w,caseId=cid,stage=stage,role=role,scenario=dict(risk=risk,aum=aum,pep=pep),note=note))
                st.session_state['_simulation']=result
            except ValueError as e: st.error(str(e))
    if '_simulation' in st.session_state:
        for r in st.session_state['_simulation']['routes']:
            with st.container(border=True):
                st.markdown('**'+r['label']+' → '+r['target']+'**')
                if r['eligible']: st.success('Eligible: all configured checks pass')
                else:
                    for issue in r['issues']: st.write(':material/block: '+issue)
        with st.expander('Documents required for this scenario'): st.write(st.session_state['_simulation']['requiredDocuments'])
    st.divider();st.subheader('Publish a controlled version')
    st.caption('Only Compliance can publish. Existing cases remain on their current workflow version.')
    if st.button('Validate the draft',icon=':material/fact_check:'):
        try: st.success(api().request('/workflow/validate','POST',{'workflow':w})['message'])
        except ValueError as e: st.error(str(e))
    with st.form('publish_workflow'):
        note=st.text_area('What changed in this version?')
        if st.form_submit_button('Publish workflow',type='primary',disabled=st.session_state['_workflow_dirty']):
            try:
                api().request('/workflow/publish','POST',dict(draftRevision=st.session_state['_workflow_revision'],note=note))
                st.session_state.pop('_workflow_edit');st.session_state['_notice']='Workflow published. New cases use the new version.';st.rerun()
            except ValueError as e: st.error(str(e))
    if st.session_state['_workflow_dirty']: st.warning('Save your draft before publishing.')
    with st.expander('Migrate selected existing cases'):
        candidates=[c for c in data['cases'] if c['workflowVersion']!=data['workflow']['version'] and c['stageKind'] not in ['approval','closed']]
        st.caption('Stage names and purposes must match. Working-case review checks reset. Approval and closed cases cannot migrate.')
        with st.form('migrate_cases'):
            ids=st.multiselect('Cases to migrate',[c['id'] for c in candidates],format_func=lambda uid:next(c['name'] for c in candidates if c['id']==uid))
            note=st.text_input('Migration reason')
            if st.form_submit_button('Migrate selected cases'):
                try: api().request('/workflow/migrate','POST',dict(caseIds=ids,note=note));st.session_state['_notice']='Selected cases migrated';st.rerun()
                except ValueError as e: st.error(str(e))
else:
    st.subheader('Configuration history')
    st.dataframe(data['configAudit'],hide_index=True)
    bundle=api().request('/config/export')
    st.download_button('Export configuration',json.dumps(bundle,indent=2),file_name='aurelia-configuration.json',mime='application/json',icon=':material/download:')
    with st.expander('Import a workflow as draft'):
        st.caption('Only the workflow is imported. Current policies and UI settings remain unchanged. Custom field references must already exist.')
        imported=st.file_uploader('Configuration JSON',type=['json'])
        if st.button('Import draft',disabled=imported is None):
            try:
                api().request('/config/import','POST',json.loads(imported.getvalue()));st.session_state.pop('_workflow_edit',None);st.rerun()
            except (ValueError,TypeError) as e: st.error(str(e))
