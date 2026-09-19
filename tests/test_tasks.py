import pytest
from datetime import date, timedelta
from clm.web import create_app

@pytest.fixture
def client(tmp_path):
    c=create_app(dict(DATA_DIR=str(tmp_path),TESTING=True,SECRET_KEY="tasks-test")).test_client()
    c.get('/api/state');return c


def role(c,r,cid=None):
    b=dict(role=r)
    if cid:b['clientId']=cid
    assert c.post('/api/session',json=b).status_code==200


def make(c,owner='Client'):
    payload=dict(title='Provide source evidence',detail='Upload sale agreement then respond.',owner=owner,priority='High',category='Source of wealth',dueDate=(date.today()+timedelta(days=7)).isoformat())
    r=c.post('/api/cases/CLM-2026-1041/tasks',json=payload)
    assert r.status_code==201,r.json
    return r.json,payload


def test_client_response_acceptance_and_case_isolation(client):
    t,b=make(client);p='/api/cases/CLM-2026-1041/tasks/'+t['id']
    role(client,'Client','CLM-2026-1042')
    assert client.patch(p,json=dict(revision=1,action='submit',note='Other case')).status_code==404
    role(client,'Client','CLM-2026-1041')
    assert client.patch(p,json=dict(revision=1,action='complete',note='Cannot approve myself')).status_code==400
    assert client.patch(p,json=dict(revision=1,action='submit',note='Synthetic evidence supplied in Documents')).status_code==200
    role(client,'Relationship manager')
    assert client.patch(p,json=dict(revision=1,action='complete',note='Stale update')).status_code==400
    assert client.patch(p,json=dict(revision=2,action='complete',note='Response inspected and accepted')).status_code==200
    t=next(c for c in client.get('/api/state').json['cases'] if c['id']=='CLM-2026-1041')['tasks'][0]
    assert t['status']=='Completed' and len(t['history'])==2
    assert client.patch(p,json=dict(revision=3,action='reopen',note='More evidence needed')).status_code==200


def test_staff_assignments_are_private_and_role_enforced(client):
    t,b=make(client,'Compliance');p='/api/cases/CLM-2026-1041/tasks/'+t['id']
    assert client.post('/api/cases/CLM-2026-1041/tasks',json=b).status_code==400
    assert client.patch(p,json=dict(revision=1,action='complete',note='Wrong role')).status_code==400
    role(client,'Client','CLM-2026-1041')
    assert client.get('/api/state').json['cases'][0]['tasks']==[]
    assert client.post('/api/cases/CLM-2026-1041/tasks',json=b).status_code==400
    role(client,'Compliance')
    assert client.patch(p,json=dict(revision=1,action='complete',note='Owner finished')).status_code==200
