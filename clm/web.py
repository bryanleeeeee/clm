"""Flask API and static browser application. All business logic runs in Python."""
import base64
import binascii
import io
import os
import re
import secrets
import math
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
from flask import Flask, jsonify, request, session, send_file, send_from_directory
from werkzeug.exceptions import HTTPException
from .defaults import ROLES, STAFF, CHECKS, FIELDS, GUARDS, KINDS, now, date_after
from .domain import (ValidationError, require, text, event, audit, requirements, stage_for, workflow_for,
                     validate_ui, validate_rules, validate_workflow, matches, guard_issues, execute, case_view)
from .store import Store

ROOT=Path(__file__).resolve().parent.parent

def create_app(config=None):
    app=Flask(__name__,static_folder=None)
    app.config.update(DATA_DIR=os.environ.get('DATA_DIR',str(ROOT/'data')),MAX_CONTENT_LENGTH=15*1024*1024,SESSION_COOKIE_NAME='aurelia_python',SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Strict',SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE','0')=='1',PERMANENT_SESSION_LIFETIME=timedelta(hours=8))
    if config: app.config.update(config)
    store=Store(app.config['DATA_DIR']);app.extensions['store']=store
    secret=os.environ.get('SECRET_KEY') or app.config.get('SECRET_KEY')
    if not secret:
        secret_file=store.directory/'.session-key'
        try:
            with secret_file.open('x',encoding='utf-8') as f: f.write(secrets.token_hex(32))
            try: secret_file.chmod(0o600)
            except OSError: pass
        except FileExistsError: pass
        secret=secret_file.read_text(encoding='utf-8')
    app.secret_key=secret

    @app.before_request
    def access():
        if request.path.startswith('/api/'):
            origin=request.headers.get('Origin')
            if request.method not in ['GET','HEAD','OPTIONS'] and origin:
                require(urlparse(origin).netloc==request.host,'Cross-origin request rejected')
            if 'role' not in session:
                with store.transaction() as (db,_): first=db['cases'][0]['id']
                session.update(role='Relationship manager',clientId=first)
                session.permanent=True

    @app.after_request
    def headers(response):
        response.headers['Cache-Control']='no-store' if request.path.startswith('/api/') else 'no-cache'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        return response

    @app.errorhandler(ValidationError)
    def validation(error): return jsonify(error=str(error)),400
    @app.errorhandler(HTTPException)
    def http_error(error): return jsonify(error=error.description),error.code

    def body():
        value=request.get_json()
        require(isinstance(value,dict),'Expected a JSON object')
        return value
    def staff(): require(session['role'] in STAFF,'Staff access is required')
    def role(*roles): require(session['role'] in roles,'Required role: '+', '.join(roles))
    def get_case(db,identifier):
        c=next((c for c in db['cases'] if c['id']==identifier),None)
        if c is None or (session['role']=='Client' and session['clientId']!=identifier):
            from flask import abort
            abort(404,description='Case not found')
        return c
    def editable(c,db): require(stage_for(c,db)['editable'],'This stage is locked; open a review or return for remediation')
    def success(): return jsonify(ok=True)

    @app.get('/api/state')
    def state():
        with store.transaction() as (db,_):
            clients=[case_view(c,db,session['role']) for c in db['cases'] if session['role']!='Client' or c['id']==session['clientId']]
            result={k:deepcopy(v) for k,v in db.items() if k not in ['cases','workflowVersions']}
            result.update(cases=clients,session=dict(session),stages=list(dict.fromkeys([s['name'] for s in db['workflow']['stages']]+[c['stage'] for c in clients])),schema=dict(roles=ROLES,staff=STAFF,checks=CHECKS,fields=FIELDS,guards=GUARDS,kinds=KINDS),synthetic=True)
            if session['role']=='Client':
                result.pop('configAudit',None);result.pop('workflowDraft',None)
                for c in clients: c['activity']=[]
            return jsonify(result)

    @app.post('/api/session')
    def switch_role():
        b=body();require(b.get('role') in ROLES,'Invalid role')
        with store.transaction() as (db,_):
            cid=b.get('clientId',session['clientId'])
            require(any(c['id']==cid for c in db['cases']),'Choose a valid client')
        session.update(role=b['role'],clientId=cid)
        return jsonify(dict(session))

    @app.post('/api/cases')
    def create_case():
        staff();b=body()
        name=text(b.get('name'),'Client name',120);email=text(b.get('email'),'Email',160)
        require(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email),'Enter a valid email')
        require(b.get('type') in ['Individual','Company','Family office'],'Invalid client type')
        require(b.get('risk') in ['Low','Medium','High'],'Invalid risk')
        try: aum=float(b.get('aum',0))
        except (ValueError,TypeError): raise ValidationError('Assets must be a number')
        require(math.isfinite(aum) and 0<=aum<=100000,'Assets must be between 0 and 100,000 SGD million')
        with store.transaction(True) as (db,_):
            number=max([1040]+[int(c['id'].split('-')[-1]) for c in db['cases']])+1
            w=db['workflow']
            c=dict(id=f'CLM-2026-{number}',name=name,email=email,type=b['type'],risk=b['risk'],residency=text(b.get('residency','Singapore'),'Residence',100),taxResidency='',sourceOfWealth='',aum=aum,owner=text(b.get('owner','Sarah Chen'),'Owner',100),phone='',pep=bool(b.get('pep')),consent=False,stage=w['startStage'],workflowVersion=w['version'],createdAt=now(),dueDate=date_after(db['settings']['slaDays']),kyc={key:False for key in CHECKS},customFields={},documents=[],activity=[])
            event(c,session['role'],'Onboarding case created','Synthetic client record');db['cases'].insert(0,c)
            result=deepcopy(c)
        return jsonify(result),201

    @app.patch('/api/cases/<identifier>')
    def update_case(identifier):
        b=body()
        with store.transaction(True) as (db,_):
            c=get_case(db,identifier);editable(c,db)
            for key in ['email','phone','residency','taxResidency','sourceOfWealth']:
                if key in b:
                    value=text(b[key],key,2000,True)
                    if key=='email': require(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value),'Enter a valid email')
                    c[key]=value
            if 'consent' in b: require(type(b['consent']) is bool,'Declaration must be true/false');c['consent']=b['consent']
            if session['role']!='Client':
                if 'risk' in b: require(b['risk'] in ['Low','Medium','High'],'Invalid risk');c['risk']=b['risk']
                if 'pep' in b: require(type(b['pep']) is bool,'PEP must be true/false');c['pep']=b['pep']
                if 'owner' in b: c['owner']=text(b['owner'],'Owner',100)
            custom=b.get('customFields',{})
            require(isinstance(custom,dict),'Invalid custom field values')
            fields={f['key']:f for f in db['ui']['customFields']}
            for key,value in custom.items():
                require(key in fields,'Unknown form field')
                f=fields[key]
                require(session['role']!='Client' or f['clientEditable'],f'{f["label"]} is staff-only')
                if f['type']=='checkbox': require(type(value) is bool,'Checkbox requires true/false')
                elif f['type']=='number' and value!='': require(type(value) in [int,float] and math.isfinite(value),'Enter a finite number')
                else:
                    value=text(value,f['label'],2000,True)
                    if f['type']=='select' and value: require(value in f['options'],'Choose a configured option')
                    if f['type']=='date' and value:
                        from datetime import date
                        try: date.fromisoformat(value)
                        except ValueError: raise ValidationError('Enter a valid date')
                c['customFields'][key]=value
            c['kyc']={k:False for k in CHECKS};event(c,session['role'],'Client profile updated','Due diligence checks reset')
        return success()

    @app.post('/api/cases/<identifier>/transition')
    def transition_case(identifier):
        b=body();staff()
        with store.transaction(True) as (db,_):
            execute(get_case(db,identifier),db,b.get('action'),session['role'],text(b.get('note',''),'Decision note',2000,True))
        return success()

    @app.put('/api/cases/<identifier>/kyc')
    def kyc(identifier):
        role('Compliance');b=body()
        require(b.get('check') in CHECKS and type(b.get('checked')) is bool,'Choose a valid check and outcome')
        note=text(b.get('note'),'Review note',2000)
        with store.transaction(True) as (db,_):
            c=get_case(db,identifier);require(stage_for(c,db)['kind']=='review','Due diligence must be in progress')
            c['kyc'][b['check']]=b['checked'];event(c,session['role'],f'{b["check"]} check '+('completed' if b['checked'] else 'reopened'),note)
        return success()

    @app.post('/api/cases/<identifier>/notes')
    def notes(identifier):
        staff();note=text(body().get('note'),'Note',2000)
        with store.transaction(True) as (db,_):
            c=get_case(db,identifier);require(stage_for(c,db)['kind']!='closed','Closed cases are read-only');event(c,session['role'],'Case note added',note)
        return success()

    @app.post('/api/cases/<identifier>/documents')
    def upload(identifier):
        b=body();name=text(b.get('name'),'File name',160)
        require(re.search(r'\.(pdf|png|jpe?g)$',name,re.I),'Only PDF, PNG and JPEG files are supported')
        try: content=base64.b64decode(b.get('content',''),validate=True)
        except (ValueError,TypeError,binascii.Error): raise ValidationError('Invalid file encoding')
        require(0<len(content)<=10*1024*1024,'File must be between 1 byte and 10 MB')
        ext=name.rsplit('.',1)[-1].lower()
        require(content.startswith(b'%PDF-') if ext=='pdf' else content.startswith(b'\x89PNG\r\n\x1a\n') if ext=='png' else content.startswith(b'\xff\xd8\xff'),'File signature does not match its extension')
        with store.transaction(True) as (db,conn):
            c=get_case(db,identifier);editable(c,db);require(b.get('type') in requirements(c,db),'Choose a configured document category')
            uid=str(uuid4());conn.execute('INSERT INTO files VALUES (?,?)',(uid,content))
            c['documents'].append(dict(id=uid,name=name.replace('\\','/').split('/')[-1],type=b['type'],size=len(content),status='Pending review',uploadedAt=now()))
            event(c,session['role'],'Document uploaded',b['type'])
        return jsonify(ok=True),201

    @app.post('/api/cases/<identifier>/documents/<document_id>/review')
    def review_document(identifier,document_id):
        role('Compliance','Operations');b=body();require(b.get('status') in ['Verified','Rejected'],'Choose a valid outcome');note=text(b.get('note'),'Review note',2000)
        with store.transaction(True) as (db,_):
            c=get_case(db,identifier);editable(c,db);d=next((d for d in c['documents'] if d['id']==document_id),None);require(d is not None,'Document not found')
            d.update(status=b['status'],reviewNote=note);event(c,session['role'],'Document '+b['status'].lower(),d['type']+': '+note)
        return success()

    @app.get('/api/cases/<identifier>/documents/<document_id>')
    def download(identifier,document_id):
        with store.transaction() as (db,conn):
            c=get_case(db,identifier);d=next((d for d in c['documents'] if d['id']==document_id),None);require(d is not None,'Document not found')
            content=b'SYNTHETIC DATA - NOT REAL CLIENT DATA\nIllustrative document; not identity evidence.' if d.get('sample') else conn.execute('SELECT content FROM files WHERE id=?',(document_id,)).fetchone()[0]
            name=d['name']
        return send_file(io.BytesIO(content),as_attachment=True,download_name=name,mimetype='application/octet-stream')

    @app.put('/api/rules')
    def save_rules():
        role('Compliance');b=body()
        with store.transaction(True) as (db,_):
            require(b.get('revision')==db['revision'],'Configuration changed; refresh before saving')
            db['rules']=validate_rules(b.get('rules'),db['ui']);audit(db,session['role'],'Policy configuration saved')
        return success()

    @app.put('/api/settings')
    def save_settings():
        role('Operations');b=body();name=text(b.get('bankName'),'Institution name',100)
        try: days=int(b.get('slaDays'))
        except (ValueError,TypeError): raise ValidationError('Target must be an integer')
        require(1<=days<=90 and str(days)==str(b['slaDays']),'Target must be 1–90 days')
        with store.transaction(True) as (db,_):
            db['settings'].update(bankName=name,slaDays=days);audit(db,session['role'],'Workspace settings updated')
        return success()

    @app.put('/api/ui')
    def save_ui():
        role('Operations');b=body()
        with store.transaction(True) as (db,_):
            require(b.get('revision')==db['revision'],'Configuration changed; refresh before saving')
            db['ui']=validate_ui(b.get('ui',{}),db);audit(db,session['role'],'UI and form configuration saved')
        return success()

    @app.put('/api/workflow/draft')
    def save_draft():
        role('Compliance','Operations');b=body()
        with store.transaction(True) as (db,_):
            require(b.get('draftRevision')==db['draftRevision'],'Draft changed; reload the latest version')
            w=b.get('workflow');require(isinstance(w,dict) and isinstance(w.get('stages'),list) and isinstance(w.get('transitions'),list),'Invalid workflow draft')
            require(len(w['stages'])<=30 and len(w['transitions'])<=120,'Draft exceeds limits')
            # Incomplete drafts may be saved; validation is mandatory before publishing.
            db['workflowDraft']=deepcopy(w);db['draftRevision']+=1;audit(db,session['role'],'Workflow draft saved')
        return success()

    @app.post('/api/workflow/validate')
    def validate_draft():
        staff();b=body()
        with store.transaction() as (db,_):
            validate_workflow(b.get('workflow',db['workflowDraft']),db['ui'])
        return jsonify(ok=True,message='All stages are reachable, routes are valid and mandatory controls are present.')

    @app.post('/api/workflow/publish')
    def publish():
        role('Compliance');b=body();note=text(b.get('note'),'Publication note',1000)
        with store.transaction(True) as (db,_):
            require(b.get('draftRevision')==db['draftRevision'],'Draft changed; reload before publishing')
            w=validate_workflow(db['workflowDraft'],db['ui']);w['version']=db['workflow']['version']+1
            db['workflow']=w;db['workflowVersions'][str(w['version'])]=deepcopy(w);db['workflowDraft']=deepcopy(w);db['draftRevision']+=1
            audit(db,session['role'],f'Workflow v{w["version"]} published',note)
        return success()

    @app.post('/api/workflow/simulate')
    def simulate():
        staff();b=body()
        with store.transaction() as (db,_):
            w=b.get('workflow',db['workflowDraft']);validate_workflow(w,db['ui'])
            c=deepcopy(get_case(db,b.get('caseId')))
            for k in FIELDS:
                if k in b.get('scenario',{}): c[k]=b['scenario'][k]
            c['stage']=b.get('stage',c['stage']);require(any(s['name']==c['stage'] for s in w['stages']),'Select a stage in the draft')
            actor=b.get('role',session['role']);require(actor in STAFF,'Choose a staff role')
            results=[]
            for r in w['transitions']:
                if r['source']!=c['stage']: continue
                issues=guard_issues(c,db,r['guards'],actor,b.get('note',''))
                if actor not in r['roles']: issues.append('Role is not permitted')
                if not matches(r['conditions'],c): issues.append('Routing conditions do not match')
                target=next(s for s in w['stages'] if s['name']==r['target'])
                if target['kind']=='active' and stage_for(c,db,w)['kind']=='review' and not c.get('activatedAt'): issues.append('First activation requires independent approval')
                results.append(dict(label=r['label'],target=r['target'],eligible=not issues,issues=issues))
            return jsonify(routes=results,requiredDocuments=requirements(c,db))

    @app.post('/api/workflow/migrate')
    def migrate_cases():
        role('Compliance');b=body();note=text(b.get('note'),'Migration reason',1000)
        require(isinstance(b.get('caseIds'),list) and 1<=len(b['caseIds'])<=1000,'Select cases to migrate')
        with store.transaction(True) as (db,_):
            w=db['workflow'];stages={s['name']:s for s in w['stages']}
            for uid in b['caseIds']:
                c=get_case(db,uid);old=stage_for(c,db)
                require(c['stage'] in stages and old['kind']==stages[c['stage']]['kind'],'Stage names and types must match before migrating existing cases')
                require(old['kind'] not in ['closed','approval'],'Closed and approval cases cannot be migrated')
                c['workflowVersion']=w['version']
                if old['editable']: c['kyc']={k:False for k in CHECKS}
                event(c,session['role'],f'Migrated to workflow v{w["version"]}',note)
            audit(db,session['role'],'Existing cases migrated',note)
        return success()

    @app.get('/api/config/export')
    def export_config():
        staff()
        with store.transaction() as (db,_):
            result=dict(format='aurelia-config-v2',synthetic=True,workflow=db['workflow'],rules=db['rules'],ui=db['ui'],settings=db['settings'])
        return jsonify(result)

    @app.post('/api/config/import')
    def import_config():
        role('Compliance');b=body();require(b.get('format')=='aurelia-config-v2','Unsupported configuration format')
        with store.transaction(True) as (db,_):
            # Import only a workflow draft; live UI/rules remain untouched until their own editors save.
            validate_workflow(b.get('workflow',{}),db['ui'])
            db['workflowDraft']=deepcopy(b['workflow']);db['draftRevision']+=1;audit(db,session['role'],'Workflow configuration imported as draft')
        return success()

    @app.get('/health')
    def health(): return jsonify(status='ok',runtime='python-flask',synthetic=True)
    @app.get('/')
    def index(): return send_from_directory(ROOT/'public','index.html')
    @app.get('/<path:filename>')
    def static_asset(filename): return send_from_directory(ROOT/'public',filename)
    return app
