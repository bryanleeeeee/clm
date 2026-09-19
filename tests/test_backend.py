import base64
from copy import deepcopy
import pytest
from clm.web import create_app
from clm.domain import validate_workflow, ValidationError, requirements, matches
from clm.defaults import seed

@pytest.fixture
def app(tmp_path):
    return create_app({'DATA_DIR':str(tmp_path),'TESTING':True,'SECRET_KEY':'test-only-secret'})

@pytest.fixture
def client(app):
    c=app.test_client();c.get('/api/state');return c

def call(c,path,method='GET',body=None,status=200):
    r=c.open('/api'+path,method=method,json=body)
    assert r.status_code==status,r.get_json()
    return r.get_json()

def role(c,name,cid=None):
    body={'role':name}
    if cid: body['clientId']=cid
    return call(c,'/session','POST',body)

def test_full_lifecycle_persistence_and_access(app,client):
    c=call(client,'/cases','POST',dict(name='Python Journey',email='python@example.com',type='Individual',risk='Low',residency='Singapore',aum=5),201)
    uid=c['id'];p='/cases/'+uid
    call(client,p+'/transition','POST',{'action':'Submit for review'},400)
    role(client,'Client',uid)
    assert len(call(client,'/state')['cases'])==1
    call(client,'/cases/CLM-2026-1041/documents/seed-0-0',status=404)
    call(client,'/cases','POST',{},400)
    call(client,p,'PATCH',dict(taxResidency='Singapore',sourceOfWealth='Synthetic salary',consent=True))
    call(client,p+'/documents','POST',dict(name='fake.pdf',type='Identity document',content=base64.b64encode(b'not pdf').decode()),400)
    for name in call(client,'/state')['cases'][0]['requiredDocuments']:
        call(client,p+'/documents','POST',dict(name='test.pdf',type=name,content=base64.b64encode(b'%PDF-1.4\nSynthetic fixture\n%%EOF').decode()),201)
    role(client,'Relationship manager');call(client,p+'/transition','POST',{'action':'Submit for review'})
    call(client,p+'/transition','POST',{'action':'Request approval'},400)
    role(client,'Compliance')
    record=next(c for c in call(client,'/state')['cases'] if c['id']==uid)
    for d in record['documents']: call(client,p+'/documents/'+d['id']+'/review','POST',dict(status='Verified',note='Synthetic evidence reviewed'))
    from test_wealth import approve_dossier
    approve_dossier(client,uid)
    for check in ['identity','screening','wealth','tax']: call(client,p+'/kyc','PUT',dict(check=check,checked=True,note='Review recorded'))
    # Compliance cannot submit to itself in the default workflow.
    call(client,p+'/transition','POST',{'action':'Request approval'},400)
    role(client,'Relationship manager');call(client,p+'/transition','POST',{'action':'Request approval'})
    call(client,p,'PATCH',{'sourceOfWealth':'Locked'},400)
    role(client,'Compliance');call(client,p+'/transition','POST',{'action':'Approve & activate'})
    call(client,p+'/transition','POST',{'action':'Start periodic review'})
    call(client,p+'/transition','POST',{'action':'Complete periodic review'},400)
    approve_dossier(client,uid)
    for check in ['identity','screening','wealth','tax']: call(client,p+'/kyc','PUT',dict(check=check,checked=True,note='Fresh periodic evidence'))
    call(client,p+'/transition','POST',{'action':'Complete periodic review'})
    call(client,p+'/transition','POST',{'action':'Offboard client','note':'short'},400)
    call(client,p+'/transition','POST',{'action':'Offboard client','note':'Synthetic closure request'})
    call(client,p,'PATCH',{'residency':'France'},400)
    restarted=create_app({'DATA_DIR':app.config['DATA_DIR'],'TESTING':True,'SECRET_KEY':'test-only-secret'})
    records=restarted.test_client().get('/api/state').json['cases']
    assert next(c for c in records if c['id']==uid)['stage']=='Offboarded'
    content=client.get('/api'+p+'/documents/'+record['documents'][0]['id']).data
    assert b'Synthetic fixture' in content

def test_atomic_profile_validation(client):
    data=call(client,'/state');c=data['cases'][0]
    call(client,'/cases/'+c['id'],'PATCH',dict(email='valid@example.com',risk='Invalid'),400)
    assert call(client,'/state')['cases'][0]['email']==c['email']

def test_versioned_workflow_insert_publish_and_pinning(client):
    role(client,'Compliance');data=call(client,'/state');w=deepcopy(data['workflowDraft'])
    route=next(r for r in w['transitions'] if r['label']=='Submit for review');continuation=deepcopy(route)
    route.update(target='Suitability review',label='Start suitability')
    continuation.update(id='route-custom',source='Suitability review')
    w['stages'].insert(2,dict(name='Suitability review',kind='custom',owner='Relationship manager',description='Review investment needs',slaDays=3,editable=True))
    w['transitions'].append(continuation)
    call(client,'/workflow/draft','PUT',dict(workflow=w,draftRevision=data['draftRevision']))
    call(client,'/workflow/validate','POST',{})
    fresh=call(client,'/state')
    call(client,'/workflow/publish','POST',dict(draftRevision=fresh['draftRevision'],note='Add suitability review'))
    fresh=call(client,'/state');assert fresh['workflow']['version']==2
    assert all(c['workflowVersion']==1 for c in fresh['cases'])
    new=call(client,'/cases','POST',dict(name='Version two',email='v2@example.com',type='Individual',risk='Low',aum=1),201)
    assert new['workflowVersion']==2
    call(client,'/workflow/draft','PUT',dict(workflow=w,draftRevision=data['draftRevision']),400)
    current=call(client,'/state');uid=next(c['id'] for c in current['cases'] if c['stage']=='Documentation' and c['workflowVersion']==1)
    call(client,'/workflow/migrate','POST',dict(caseIds=[uid],note='Approved migration to suitability journey'))
    assert next(c for c in call(client,'/state')['cases'] if c['id']==uid)['workflowVersion']==2

def test_graph_and_approval_controls():
    db=seed();w=deepcopy(db['workflow']);r=next(r for r in w['transitions'] if r['label']=='Approve & activate');r['guards']=[]
    with pytest.raises(ValidationError,match='mandatory'): validate_workflow(w,db['ui'])
    w=deepcopy(db['workflow']);w['transitions']=[r for r in w['transitions'] if r['target']!='Offboarded']
    with pytest.raises(ValidationError): validate_workflow(w,db['ui'])
    assert matches({'match':'all','items':[{'field':'risk','op':'eq','value':'High'},{'field':'aum','op':'gte','value':'10'}]},dict(risk='High',aum=12))
    assert not matches({'match':'all','items':[{'field':'risk','op':'eq','value':'High'},{'field':'aum','op':'gte','value':'10'}]},dict(risk='High',aum=2))

def test_custom_form_and_policy_enforcement(client):
    role(client,'Operations');data=call(client,'/state');ui=deepcopy(data['ui']);ui['customFields']=[dict(key='objective',label='Investment objective',type='select',options=['Growth','Income'],required=True,clientEditable=True),dict(key='staff_note',label='Staff note',type='text',options=[],required=False,clientEditable=False)]
    call(client,'/ui','PUT',dict(ui=ui,revision=data['revision']))
    role(client,'Compliance');data=call(client,'/state');rules=deepcopy(data['rules'])
    rules.append(dict(id='large-assets',name='Large assets evidence',enabled=True,description='Combined conditions',conditions={'match':'all','items':[dict(field='risk',op='eq',value='High'),dict(field='aum',op='gte',value='10')]},documents=['Independent wealth report'],requiredFields=['objective']))
    call(client,'/rules','PUT',dict(rules=rules,revision=data['revision']))
    data=call(client,'/state');c=data['cases'][0];assert 'Independent wealth report' in c['requiredDocuments'];assert 'objective' in c['requiredFields']
    role(client,'Client',c['id'])
    call(client,'/cases/'+c['id'],'PATCH',{'customFields':{'staff_note':'unauthorized'}},400)
    call(client,'/cases/'+c['id'],'PATCH',{'customFields':{'objective':'Invalid'}},400)
    call(client,'/cases/'+c['id'],'PATCH',{'customFields':{'objective':'Growth'}})
    assert call(client,'/state')['cases'][0]['customFields']['objective']=='Growth'
    role(client,'Operations');fresh=call(client,'/state');ui=fresh['ui'];ui['customFields']=[]
    call(client,'/ui','PUT',dict(ui=ui,revision=fresh['revision']),400)

def test_simulation_is_read_only_and_configuration_export_safe(client):
    data=call(client,'/state');r=call(client,'/workflow/simulate','POST',dict(caseId=data['cases'][0]['id'],stage='Documentation',role='Relationship manager',scenario={'risk':'High','pep':True}))
    assert any('must be uploaded' in issue for route in r['routes'] for issue in route['issues'])
    assert call(client,'/state')['revision']==data['revision']
    exported=call(client,'/config/export');assert 'cases' not in exported and 'SECRET_KEY' not in exported
    role(client,'Client',data['cases'][0]['id']);call(client,'/config/export',status=400)

def test_banner_static_and_health(client):
    assert b'SYNTHETIC DATA' in client.get('/').data
    assert client.get('/health').json['runtime']=='python-flask'
    assert client.get('/../clm/web.py').status_code==404
