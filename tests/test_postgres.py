"""Live PostgreSQL integration check; runs only with TEST_DATABASE_URL set."""
import base64
import os
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from clm.web import create_app

@pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'),reason='Set TEST_DATABASE_URL for live storage verification')
def test_postgres_persistence_rollback_and_concurrency():
    from psycopg import sql
    url=os.environ['TEST_DATABASE_URL'];schema='bankclm_test_'+uuid4().hex
    config=dict(DATABASE_URL=url,DATABASE_SCHEMA=schema,SECRET_KEY='isolated-integration-test',TESTING=True)
    app=create_app(config);store=app.extensions['store']
    try:
        c=app.test_client();assert c.get('/api/state').status_code==200
        response=c.post('/api/cases',json=dict(name='Synthetic persistence check',email='test@example.com',type='Individual',risk='Low',aum=5,owner='Test RM',residency='Singapore'))
        assert response.status_code==201
        cid=response.json['id'];content=b'%PDF-1.4\nSynthetic storage test'
        assert c.post('/api/cases/'+cid+'/documents',json=dict(name='synthetic.pdf',type='Account opening form',content=base64.b64encode(content).decode())).status_code==201
        fresh=create_app(config).test_client()
        case=next(x for x in fresh.get('/api/state').json['cases'] if x['id']==cid)
        assert fresh.get('/api/cases/'+cid+'/documents/'+case['documents'][0]['id']).data==content
        with pytest.raises(RuntimeError):
            with store.transaction(True) as (db,conn):
                db['settings']['bankName']='Should roll back'
                store.put_file(conn,'rollback-file',b'never persist')
                raise RuntimeError('Intentional rollback')
        with store.transaction() as (db,conn):
            assert db['settings']['bankName']!='Should roll back'
            assert store.get_file(conn,'rollback-file') is None
        def update(i):
            with store.transaction(True) as (db,_): db.setdefault('concurrency_checks',[]).append(i)
        with ThreadPoolExecutor(max_workers=4) as pool: list(pool.map(update,range(4)))
        with store.transaction() as (db,_): assert sorted(db['concurrency_checks'])==list(range(4))
    finally:
        # Only remove the isolated, randomly named schema created by this test.
        assert schema.startswith('bankclm_test_') and len(schema)==45
        with store.connect() as conn: conn.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(schema)))
