"""Evidence-linked source-of-wealth dossiers. Deterministic assistance, human decisions."""
from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
import math
import re
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlparse
from uuid import uuid4

from .defaults import now
from .domain import require, text, event

CATEGORIES = ['Business ownership', 'Business sale', 'Employment', 'Inheritance / gift', 'Property', 'Investments', 'Other']
POLICY = dict(coverage=80, enhancedCoverage=100, materiality=10, tolerance=10, freshnessDays=365)


EVIDENCE_GUIDANCE = {
    'Business ownership': 'Audited accounts, ownership register and evidence of retained earnings or dividends.',
    'Business sale': 'Sale agreement, completion statement, original investment cost and ownership register.',
    'Employment': 'Employment history, remuneration records, tax returns and a reasonable savings calculation.',
    'Inheritance / gift': 'Probate or gift records, distribution evidence and the donor’s underlying wealth history.',
    'Property': 'Acquisition cost, title records, sale completion statement and financing repayment.',
    'Investments': 'Portfolio history, realised gains and contributions; distinguish returns from reinvested principal.',
    'Other': 'Primary records that explain the economic activity, ownership and net wealth generated.'
}


def contribution(e):
    value = Decimal(str(e['amount'])) * Decimal(str(e['fxRate'])) * Decimal(str(e['ownership'])) / 100 - Decimal(str(e['deductions']))
    return float(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def event_fingerprint(events, ids):
    return sha256(json.dumps(sorted([e for e in events if e['id'] in ids], key=lambda e:e['id']), sort_keys=True).encode()).hexdigest()


def number(value, label, maximum=1e12):
    require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= maximum, f'{label} must be a finite number between 0 and {maximum:g}')
    return round(value, 6)


def dated(value, label, optional=False):
    if optional and not value: return ''
    value = text(value, label, 10)
    try: parsed = date.fromisoformat(value)
    except ValueError: require(False, f'{label} must be a valid date')
    require(parsed <= date.today(), f'{label} cannot be in the future')
    return value


def dossier(c):
    return deepcopy(c.get('wealth', dict(revision=0, status='Not started', profile={}, events=[], evidence=[], narrative='', reviews=[], updatedAt=None)))


def policy(db):
    return db.get('wealthPolicy', POLICY)


def fingerprint(c, db):
    w = dossier(c)
    data = {k: w[k] for k in ['profile', 'events', 'evidence', 'narrative']}
    data.update(client={k: c.get(k) for k in ['name','risk','pep','residency','sourceOfWealth']}, documents=c['documents'], policy=policy(db))
    return sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def approved(c, db):
    w = c.get('wealth', {})
    return w.get('status') == 'Approved' and w.get('approvedFingerprint') == fingerprint(c, db) and assessment(c, db, include_status=False)['ready']


def assessment(c, db, include_status=True):
    w, p = dossier(c), policy(db)
    profile = w['profile']; docs = {d['id']: d for d in c['documents']}
    enhanced = c.get('pep') or c['risk'] == 'High'
    target = p['enhancedCoverage'] if enhanced else p['coverage']
    findings = []
    def add(code, message, area, severity='blocker'):
        findings.append(dict(code=code, message=message, area=area, severity=severity))
    if not profile.get('occupation') or not profile.get('background'): add('profile', 'Describe the occupation and economic background.', 'Profile')
    declared = profile.get('netWorth', 0)
    if not declared: add('net-worth', 'Record total declared net worth in SGD, separate from assets held with the bank.', 'Profile')
    if not profile.get('fundsOrigin') or not profile.get('remittingBank'): add('funds', 'Explain the opening funds and the remitting bank separately from lifetime wealth.', 'Profile')
    if profile.get('fundsAmount', 0) > declared and declared: add('funds-size', 'Opening funds exceed declared net worth; reconcile the figures.', 'Profile')
    if not w['events']: add('events', 'Add the events that explain how the client accumulated wealth.', 'Journey')
    amounts = {e['id']: contribution(e) for e in w['events']}
    total = round(sum(amounts.values()), 2)
    verified_ids = set(); corroborated = 0; material_gaps = []; matrix=[]; evidence_state={}
    evidence_issues = []
    for e in w['evidence']:
        d = docs.get(e.get('documentId'))
        fresh = (date.today() - date.fromisoformat(e['date'])).days <= p['freshnessDays'] or bool(e.get('historicalReason'))
        current = e.get('reviewedEvents') == event_fingerprint(w['events'],e['eventIds'])
        usable = current and e.get('reviewStatus') == 'Verified' and (not e.get('documentId') or d and d['status'] == 'Verified' and not d.get('sample')) and fresh
        reason = 'Ready' if usable else 'Event changed or amount review required' if not current else 'Evidence review required' if e.get('reviewStatus')!='Verified' else 'Historical relevance rationale required' if not fresh else 'Uploaded document needs verification'
        evidence_state[e['id']]=dict(usable=bool(usable),reason=reason)
        if usable: verified_ids.add(e['id'])
        else: evidence_issues.append(e['title'])
    for e in w['events']:
        support = [x for x in w['evidence'] if e['id'] in x['eventIds'] and x['id'] in verified_ids and x['independent']]
        supported=min(amounts[e['id']],max([x.get('supportedAmounts',{}).get(e['id'],0) for x in support] or [0]))
        corroborated += supported
        material=total > 0 and amounts[e['id']] / total * 100 >= p['materiality']
        if material and supported < amounts[e['id']]: material_gaps.append(e['title'])
        matrix.append(dict(id=e['id'],title=e['title'],category=e['category'],claimed=amounts[e['id']],supported=supported,gap=round(amounts[e['id']]-supported,2),material=material,evidenceIds=[x['id'] for x in support],guidance=EVIDENCE_GUIDANCE[e['category']]))
        if e['category'] == 'Inheritance / gift' and not e.get('originatorBackground'):
            add('donor-'+e['id'], f'{e["title"]}: explain the donor’s underlying source of wealth.', 'Journey')
    coverage = round(corroborated / total * 100, 1) if total else 0
    expected = round(total - profile.get('outflows', 0), 2)
    gap = round(declared - expected, 2)
    gap_pct = round(abs(gap) / declared * 100, 1) if declared else 100
    if coverage < target: add('coverage', f'Independent evidence covers {coverage:g}% of wealth contributions; this demo policy requires {target:g}%.', 'Evidence')
    if material_gaps: add('material', 'Corroborate material sources: '+', '.join(material_gaps), 'Evidence')
    if gap_pct > p['tolerance']: add('reconcile', f'Reconciliation differs by SGD {abs(gap):,.0f} ({gap_pct:g}%); resolve the wealth journey or declared net worth.', 'Profile')
    if evidence_issues: add('evidence-review', f'{len(evidence_issues)} evidence item(s) are unreviewed, rejected, stale or linked to an unverified document.', 'Evidence', 'attention')
    if enhanced and not profile.get('enhancedRationale'): add('enhanced', 'Record enhanced due diligence rationale for this high-risk / PEP relationship.', 'Profile')
    if not w['narrative']: add('narrative', 'Prepare and review the source-of-wealth write-up.', 'Write-up')
    body_narrative=w['narrative'].split('6. Evidence register')[0]
    used_citations = set(re.findall(r'\[E:([^\]]+)\]', body_narrative))
    if used_citations - {e['id'] for e in w['evidence']}: add('citations', 'The write-up contains evidence references that no longer exist. Regenerate or correct them.', 'Write-up')
    if not used_citations and w['narrative']: add('citations-missing', 'Link the write-up to evidence using the supplied citation markers.', 'Write-up')
    for row in matrix:
        if row['supported']>0 and not (used_citations & set(row['evidenceIds'])): add('citation-'+row['id'],f'{row["title"]}: cite a supporting, verified source in the narrative body.','Write-up')
    status = 'Needs refresh' if include_status and w['status'] == 'Approved' and not approved(c, db) else w['status']
    return dict(status=status, enhanced=bool(enhanced), target=target, coverage=coverage, total=total, expected=expected, declared=declared, gap=gap, gapPercent=gap_pct, amounts=amounts, verifiedEvidence=len(verified_ids), matrix=matrix, evidenceState=evidence_state, findings=findings, ready=not any(f['severity']=='blocker' for f in findings))


def validate_content(b, c):
    require(isinstance(b, dict), 'Invalid dossier')
    p = b.get('profile', {}); require(isinstance(p, dict), 'Invalid wealth profile')
    profile = {k: text(p.get(k, ''), k, 4000, True) for k in ['occupation','background','fundsOrigin','remittingBank','enhancedRationale','reconciliationNote']}
    profile.update({k: number(p.get(k, 0), k) for k in ['netWorth','outflows','fundsAmount']})
    events = b.get('events', []); evidence = b.get('evidence', [])
    require(isinstance(events, list) and len(events) <= 60, 'Use up to 60 wealth events')
    require(isinstance(evidence, list) and len(evidence) <= 120, 'Use up to 120 evidence records')
    clean_events = []; ids = set()
    for e in events:
        require(isinstance(e, dict), 'Invalid wealth event')
        uid = text(e.get('id'), 'Event ID', 80); require(re.fullmatch(r'[A-Za-z0-9-]+',uid) and uid not in ids, 'Use unique alphanumeric event IDs'); ids.add(uid)
        require(e.get('category') in CATEGORIES, 'Choose a wealth source category')
        item = dict(id=uid, category=e['category'], title=text(e.get('title'), 'Event title', 160), date=dated(e.get('date'), 'Event date'), amount=number(e.get('amount'), 'Gross value'), ownership=number(e.get('ownership',100), 'Ownership', 100), fxRate=number(e.get('fxRate',1), 'FX rate',100000), deductions=number(e.get('deductions',0), 'Deductions'))
        item.update({k: text(e.get(k,''), k, 3000, k in ['originatorBackground']) for k in ['currency','description','jurisdiction','fxSource','originatorBackground']})
        require(item['currency'] in ['SGD','USD','EUR','GBP','HKD','CNY','JPY','AUD','CHF','INR','MYR','IDR'], 'Choose a supported currency')
        require(item['fxRate'] > 0 and (item['currency'] != 'SGD' or item['fxRate'] == 1), 'Use a positive conversion rate; SGD must use 1')
        require(item['deductions'] <= item['amount'] * item['fxRate'] * item['ownership']/100, 'Deductions exceed the client’s share')
        clean_events.append(item)
    old = {e['id']:e for e in dossier(c)['evidence']}; clean_evidence=[]; seen=set()
    doc_ids = {d['id'] for d in c['documents']}
    for e in evidence:
        require(isinstance(e, dict), 'Invalid evidence record')
        uid=text(e.get('id'), 'Evidence ID',80); require(re.fullmatch(r'[A-Za-z0-9-]+',uid) and uid not in seen,'Use unique alphanumeric evidence IDs'); seen.add(uid)
        item=dict(id=uid)
        for k in ['title','issuer','reference','excerpt']: item[k]=text(e.get(k), k, 4000)
        item['date']=dated(e.get('date'), 'Evidence date')
        item['historicalReason']=text(e.get('historicalReason',''), 'Historical evidence rationale',2000,True)
        item['documentId']=text(e.get('documentId',''), 'Document ID',80,True)
        require(not item['documentId'] or item['documentId'] in doc_ids,'Evidence document must belong to this case')
        item['url']=text(e.get('url',''), 'Source URL',1000,True)
        if item['url']:
            parsed=urlparse(item['url']); require(parsed.scheme in ['http','https'] and parsed.hostname and not parsed.username,'Use an HTTP(S) source URL')
        require(item['documentId'] or item['url'], 'Link an uploaded document or a public source URL')
        require(type(e.get('independent')) is bool,'Specify whether evidence is independent');item['independent']=e['independent']
        links=e.get('eventIds'); require(isinstance(links,list) and links and all(x in ids for x in links),'Link evidence to an existing wealth event');item['eventIds']=list(dict.fromkeys(links))
        prior=old.get(uid,{})
        for k in ['reviewStatus','reviewNote','reviewedAt','reviewedBy','reviewedEvents','supportedAmounts']:
            item[k]=prior.get(k, 'Pending review' if k=='reviewStatus' else '') if all(prior.get(key)==value for key,value in item.items() if key not in ['reviewStatus','reviewNote','reviewedAt','reviewedBy','reviewedEvents','supportedAmounts']) else ('Pending review' if k=='reviewStatus' else '')
        if prior.get('reviewedEvents') != event_fingerprint(clean_events,item['eventIds']):
            item.update(reviewStatus='Pending review',reviewedEvents='',supportedAmounts={})
        if not isinstance(item.get('supportedAmounts'),dict): item['supportedAmounts']={}
        clean_evidence.append(item)
    return dict(profile=profile, events=clean_events, evidence=clean_evidence, narrative=text(b.get('narrative',''),'Write-up',30000,True))


def draft(c, db):
    w=dossier(c);a=assessment(c,db);p=w['profile']
    lines=['SOURCE OF WEALTH — HUMAN REVIEW DRAFT', 'Synthetic data — not real client data.', '', f'Client: {c["name"]} | {c["id"]}', f'Risk: {c["risk"]}; PEP: {"Yes" if c.get("pep") else "No"}.', '', '1. Background', p.get('background') or '[Background required]', 'Occupation: '+(p.get('occupation') or '[Required]'), '', '2. Wealth accumulation journey']
    for e in sorted(w['events'],key=lambda x:x['date']):
        sources=[x for x in w['evidence'] if e['id'] in x['eventIds']]
        citations=' '.join('[E:'+x['id']+']' for x in sources) or '[Corroboration required]'
        lines.append(f'{e["date"]} — {e["title"]} ({e["category"]}, {e["jurisdiction"]}). {e["description"]} Client contribution: SGD {a["amounts"][e["id"]]:,.2f}. {citations}')
        if e.get('originatorBackground'): lines.append('Donor / predecessor wealth: '+e['originatorBackground'])
    lines.extend(['', '3. Reconciliation',f'Net contributions SGD {a["total"]:,.2f}, less aggregate outflows SGD {p.get("outflows",0):,.2f}, compared with declared net worth SGD {a["declared"]:,.2f}. Unreconciled difference SGD {a["gap"]:,.2f}.',p.get('reconciliationNote',''), '', '4. Source of incoming funds',f'SGD {p.get("fundsAmount",0):,.2f} from {p.get("remittingBank") or "[Bank required]"}. {p.get("fundsOrigin") or "[Origin required]"}', '', '5. Assessment and unresolved matters',f'Independent verified coverage: {a["coverage"]}% (demo threshold {a["target"]}%).',p.get('enhancedRationale',''), *[f'- {x["message"]}' for x in a['findings'] if x['area']!='Write-up'], '', '6. Evidence register', *[f'[E:{e["id"]}] {e["title"]} — {e["issuer"]}, {e["date"]}, {e["reference"]}. Review: {e["reviewStatus"]}. Source: {e.get("url") or e.get("documentId")}' for e in w['evidence']], '', 'Prepared from recorded inputs using a deterministic template. No LLM, external screening or automatic factual verification. All statements and source relevance require human review.'])
    return '\n'.join(lines)


def touch(c, action, actor, note=''):
    w=c['wealth'];w['revision']+=1;w['updatedAt']=now();w['status']='Draft';c['kyc']['wealth']=False
    event(c,actor,action,note)


def register_wealth(app, store, body, get_case, staff, role, editable):
    from flask import jsonify, session, send_file
    import io

    @app.get('/api/cases/<identifier>/wealth')
    def read(identifier):
        staff()
        with store.transaction() as (db,_):
            c=get_case(db,identifier)
            return jsonify(dossier=dossier(c), assessment=assessment(c,db), policy=policy(db), categories=CATEGORIES, guidance=EVIDENCE_GUIDANCE)

    def locked(c,db):
        editable(c,db)
        require(dossier(c)['status']!='In review','Request changes before editing a submitted dossier')

    @app.put('/api/cases/<identifier>/wealth')
    def save(identifier):
        role('Relationship manager','Operations');b=body()
        with store.transaction(True) as (db,_):
            c=get_case(db,identifier);locked(c,db);w=dossier(c)
            require(b.get('revision')==w['revision'],'This dossier changed. Reload before saving.')
            content=validate_content(b,c)
            changed=any(content[k]!=w[k] for k in ['profile','events','evidence'])
            if changed and content['narrative']==w['narrative']: content['narrative']=''
            for kind in ['events','evidence']:
                retained={x['id'] for x in content[kind]}
                for old in w[kind]:
                    if old['id'] not in retained: w.setdefault('archivedItems',[]).append(dict(kind=kind,at=now(),value=deepcopy(old)))
            w.update(content);c['wealth']=w;touch(c,'Wealth dossier saved',session['role'])
        return jsonify(ok=True)

    @app.post('/api/cases/<identifier>/wealth/draft')
    def generate(identifier):
        role('Relationship manager','Operations');b=body()
        with store.transaction(True) as (db,_):
            c=get_case(db,identifier);locked(c,db);w=dossier(c)
            require(b.get('revision')==w['revision'],'Dossier changed; reload first')
            w['narrative']=draft(c,db);c['wealth']=w;touch(c,'Evidence-linked wealth draft prepared',session['role'])
        return jsonify(ok=True)

    @app.post('/api/cases/<identifier>/wealth/evidence/<eid>/review')
    def review_evidence(identifier,eid):
        role('Compliance','Operations');b=body()
        require(b.get('status') in ['Verified','Rejected'],'Choose a review outcome');note=text(b.get('note'),'Evidence review rationale',2000)
        with store.transaction(True) as (db,_):
            c=get_case(db,identifier);locked(c,db);w=dossier(c)
            require(b.get('revision')==w['revision'],'Dossier changed; reload first')
            e=next((e for e in w['evidence'] if e['id']==eid),None);require(e is not None,'Evidence not found')
            amounts=b.get('supportedAmounts',{})
            require(isinstance(amounts,dict),'Specify supported amounts by event')
            events={x['id']:x for x in w['events']}
            if b['status']=='Verified':
                require(set(amounts)==set(e['eventIds']),'Record the amount supported for each linked event')
                amounts={uid:number(value,'Supported amount',contribution(events[uid])) for uid,value in amounts.items()}
            else: amounts={}
            e.update(supportedAmounts=amounts,reviewedEvents=event_fingerprint(w['events'],e['eventIds']))
            e.update(reviewStatus=b['status'],reviewNote=note,reviewedAt=now(),reviewedBy=session['role']);w['narrative']='';c['wealth']=w;touch(c,'Wealth evidence '+b['status'].lower(),session['role'],e['title']+': '+note)
        return jsonify(ok=True)

    @app.post('/api/cases/<identifier>/wealth/decision')
    def decision(identifier):
        b=body();action=b.get('action');require(action in ['submit','approve','return'],'Choose a valid decision')
        if action=='submit': role('Relationship manager','Operations')
        else: role('Compliance')
        note=text(b.get('note'),'Decision rationale',4000)
        with store.transaction(True) as (db,_):
            c=get_case(db,identifier);editable(c,db);w=dossier(c)
            require(b.get('revision')==w['revision'],'Dossier changed; reload first')
            if action=='submit':
                require(w['status'] in ['Draft','Changes requested','Approved'],'Prepare or refresh the dossier first')
                require(assessment(c,db)['ready'],'Resolve all blocking findings before submission')
                w['status']='In review';w['submittedBy']=session['role'];w['submittedFingerprint']=fingerprint(c,db)
            else:
                require(w['status']=='In review','Submit the dossier for review first')
                if action=='approve':
                    require(w.get('submittedBy')!=session['role'],'Independent reviewer required')
                    require(w.get('submittedFingerprint')==fingerprint(c,db),'Evidence or policy changed after submission; return for refresh')
                    require(assessment(c,db)['ready'],'Resolve all blocking findings')
                    w['status']='Approved';w['approvedFingerprint']=fingerprint(c,db)
                    # The dedicated dossier decision is separate from the case-level KYC attestation.
                else: w['status']='Changes requested'
            w['reviews'].insert(0,dict(id=str(uuid4()),at=now(),actor=session['role'],action=action,note=note,revision=w['revision'],snapshot={**{k:deepcopy(w[k]) for k in ['profile','events','evidence','narrative']},'policy':deepcopy(policy(db)),'client':{k:c.get(k) for k in ['name','risk','pep','residency']},'documents':deepcopy(c['documents'])}))
            w['revision']+=1;w['updatedAt']=now();c['wealth']=w;event(c,session['role'],'Wealth dossier '+w['status'].lower(),note)
        return jsonify(ok=True)

    @app.get('/api/cases/<identifier>/wealth/export')
    def export(identifier):
        staff()
        with store.transaction() as (db,_):
            c=get_case(db,identifier);out=dict(synthetic=True,client=c['name'],caseId=identifier,dossier=dossier(c),assessment=assessment(c,db),policy=policy(db))
        return send_file(io.BytesIO(json.dumps(out,indent=2).encode()),mimetype='application/json',as_attachment=True,download_name=identifier+'-wealth-review.json')

    @app.get('/api/cases/<identifier>/wealth/report')
    def report(identifier):
        staff()
        from html import escape
        with store.transaction() as (db,_):
            c=get_case(db,identifier);w=dossier(c);a=assessment(c,db)
            esc=lambda v: escape(str(v))
            rows=''.join(f'<tr><td>{esc(x["title"])}</td><td>{x["claimed"]:,.2f}</td><td>{x["supported"]:,.2f}</td><td>{x["gap"]:,.2f}</td></tr>' for x in a['matrix'])
            findings=''.join('<li>'+esc(x['message'])+'</li>' for x in a['findings'])
            decisions=''.join(f'<article><h3>{esc(r["action"])} · {esc(r["actor"])}</h3><p>{esc(r["at"])} · revision {r["revision"]}</p><p>{esc(r["note"])}</p></article>' for r in w['reviews'])
            content=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wealth review {esc(identifier)}</title><style>body{{font:15px/1.7 system-ui;color:#193452;max-width:960px;margin:40px auto;padding:24px}}header{{border-bottom:3px solid #3875c5;padding-bottom:20px}}.notice{{padding:14px;background:#edf4ff}}table{{border-collapse:collapse;width:100%}}th,td{{padding:12px;text-align:left;border-bottom:1px solid #ddd}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}}article{{border-top:1px solid #ddd;padding:15px 0}}@media print{{body{{margin:0}}}}</style><div class="notice">SYNTHETIC DATA — NOT REAL CLIENT DATA</div><header><h1>Source of Wealth review</h1><h2>{esc(c['name'])}</h2><p>{esc(identifier)} · {esc(a['status'])} · revision {w['revision']} · exported {esc(now())}</p></header><h2>Evidence coverage</h2><p>Independent coverage {a['coverage']}%. Supported amounts use the strongest reviewed source per event, not the sum of overlapping sources.</p><table><thead><tr><th>Wealth event</th><th>Claimed SGD</th><th>Supported SGD</th><th>Gap SGD</th></tr></thead><tbody>{rows}</tbody></table><h2>Outstanding findings</h2><ul>{findings or '<li>No configured blocking findings.</li>'}</ul><h2>Write-up</h2><pre>{esc(w['narrative'] or 'No write-up prepared.')}</pre><h2>Decision history</h2>{decisions or '<p>No decisions recorded.</p>'}<p>Prepared from recorded inputs. Human review is required. No live AI, screening or factual verification service is connected. The JSON review pack retains full historical snapshots.</p></html>'''
        return send_file(io.BytesIO(content.encode()),mimetype='text/html',as_attachment=True,download_name=identifier+'-wealth-report.html')

    @app.put('/api/wealth-policy')
    def configure():
        role('Compliance');b=body()
        p={k:number(b.get(k),k,3650 if k=='freshnessDays' else 100) for k in POLICY}
        require(p['coverage']>0 and p['enhancedCoverage']>=p['coverage'] and p['materiality']>0 and p['freshnessDays']>=1,'Use positive thresholds and enhanced coverage at least equal to standard coverage')
        from .domain import audit
        with store.transaction(True) as (db,_):
            require(b.get('revision')==db['revision'],'Workspace changed; reload before saving')
            db['wealthPolicy']=p;audit(db,session['role'],'Wealth policy updated',json.dumps(p))
        return jsonify(ok=True)
