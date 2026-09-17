"""Synthetic defaults and editable configuration, with no JavaScript runtime."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from uuid import uuid4

ROLES = ['Relationship manager', 'Compliance', 'Operations', 'Client']
STAFF = ROLES[:3]
BASE_DOCUMENTS = ['Account opening form', 'Identity document', 'Proof of address', 'Tax self-certification']
CHECKS = {'identity': 'Identity verification', 'screening': 'Sanctions, PEP & adverse media', 'wealth': 'Source of wealth & funds', 'tax': 'Tax & regulatory declarations'}
GUARDS = {'documents_received': 'All required documents received', 'documents_verified': 'All required documents verified', 'profile_complete': 'Required profile fields complete', 'consent': 'Client declaration recorded', 'kyc_complete': 'All due diligence checks complete', 'independent_approval': 'Independent compliance approver', 'reason': 'Decision reason required'}
FIELDS = {'risk': 'Risk classification', 'type': 'Client type', 'residency': 'Country of residence', 'aum': 'Assets (SGD millions)', 'pep': 'Politically exposed person', 'taxResidency': 'Tax residency'}
NAV = ['Overview', 'Onboarding', 'Client directory', 'Document centre', 'Workflows', 'Rules & policies', 'Reports & insights']
KINDS = ['prospect', 'documents', 'review', 'approval', 'active', 'closed', 'custom']

def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

def date_after(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).date().isoformat()

def default_workflow():
    stages = []
    for name, kind, owner, desc in [
        ('Prospect', 'prospect', 'Relationship manager', 'Capture the relationship and client needs.'),
        ('Documentation', 'documents', 'Operations', 'Collect client details, declarations and supporting documents.'),
        ('Due diligence', 'review', 'Compliance', 'Review identity, screening, source of wealth and tax evidence.'),
        ('Approval', 'approval', 'Compliance', 'Record an independent approval decision.'),
        ('Active', 'active', 'Relationship manager', 'Manage the active relationship and upcoming reviews.'),
        ('Periodic review', 'review', 'Compliance', 'Refresh the client profile and supporting evidence.'),
        ('Offboarded', 'closed', 'Compliance', 'Retain the closed relationship and its decision history.')]:
        stages.append(dict(name=name, kind=kind, owner=owner, description=desc, slaDays=14, editable=kind not in ['active', 'approval', 'closed']))
    edges = [
        ('Start onboarding', 'Prospect', 'Documentation', STAFF, []),
        ('Submit for review', 'Documentation', 'Due diligence', STAFF, ['documents_received', 'consent']),
        ('Request approval', 'Due diligence', 'Approval', ['Relationship manager', 'Operations'], ['documents_verified', 'profile_complete', 'consent', 'kyc_complete']),
        ('Approve & activate', 'Approval', 'Active', ['Compliance'], list(GUARDS)[:-1]),
        ('Start periodic review', 'Active', 'Periodic review', STAFF, []),
        ('Complete periodic review', 'Periodic review', 'Active', ['Compliance'], ['documents_verified', 'profile_complete', 'consent', 'kyc_complete']),
        ('Offboard client', 'Active', 'Offboarded', ['Compliance'], ['reason'])]
    for source in ['Due diligence', 'Approval', 'Periodic review']:
        edges.append(('Return for remediation', source, 'Documentation', STAFF, ['reason']))
    transitions = [dict(id=f'route-{i+1}', label=label, source=source, target=target, roles=list(roles), guards=list(guards), conditions={'match': 'all', 'items': []}, resetChecks=label == 'Start periodic review') for i, (label, source, target, roles, guards) in enumerate(edges)]
    return dict(name='Singapore private banking onboarding', version=1, startStage='Documentation', stages=stages, transitions=transitions)

def default_ui():
    return dict(brand='AURELIA', accent='#3978d4', density='comfortable', heading='Every relationship starts here.', subtitle='A clear view of your clients, your priorities, and what comes next.', navigation=list(NAV), dashboardCards=['open', 'approval', 'attention', 'assets'], customFields=[])

def default_rules():
    result = []
    for i, (name, field, op, value, document) in enumerate([
        ('Enhanced source of wealth', 'risk', 'eq', 'High', 'Source of wealth evidence'),
        ('Politically exposed persons', 'pep', 'eq', True, 'PEP declaration'),
        ('Beneficial ownership', 'type', 'ne', 'Individual', 'Beneficial ownership register')]):
        result.append(dict(id=f'rule-{i+1}', name=name, enabled=True, description='Collect supporting evidence when the configured conditions match.', conditions={'match': 'all', 'items': [dict(field=field, op=op, value=value)]}, documents=[document], requiredFields=[]))
    return result

def seed():
    rows = [
        ('Isabelle Tan','Individual','Singapore','High','Due diligence',12.5,'Sarah Chen',2),
        ('Meridian Family Office','Family office','Singapore','Medium','Documentation',35,'James Lim',4),
        ('Alexander Wong','Individual','Hong Kong','Low','Approval',8.2,'Sarah Chen',1),
        ('Priya Mehta','Individual','Singapore','Medium','Documentation',6.8,'David Koh',6),
        ('Pacific Crest Holdings','Company','Singapore','High','Due diligence',24,'James Lim',-1),
        ('Elizabeth Chen','Individual','Singapore','Low','Active',15.4,'Sarah Chen',12),
        ('Daniel Laurent','Individual','France','Medium','Prospect',7.5,'David Koh',8),
        ('Nusantara Capital','Company','Indonesia','High','Periodic review',42,'James Lim',3),
        ('Charlotte Lee','Individual','Singapore','Low','Active',9.3,'Sarah Chen',15),
        ('Arjun Kapoor','Individual','India','Medium','Documentation',11.2,'David Koh',5),
        ('Victoria Ng','Individual','Singapore','Low','Approval',5.6,'Sarah Chen',2),
        ('William Teo','Individual','Singapore','Low','Active',18.7,'James Lim',14)]
    db = dict(rules=default_rules(), settings=dict(bankName='Aurelia Private Bank', slaDays=14, bookingCentre='Singapore', currency='SGD'), cases=[])
    for i, (name, kind, country, risk, stage, aum, owner, due) in enumerate(rows):
        advanced = stage in ['Approval', 'Active', 'Periodic review']
        docs = BASE_DOCUMENTS if advanced else BASE_DOCUMENTS[:2 if i % 3 == 0 else 3]
        db['cases'].append(dict(id=f'CLM-2026-{1041+i}', name=name, type=kind, residency=country, risk=risk, stage=stage, aum=aum, owner=owner, email=f'synthetic.client{i+1}@example.com', phone='+65 8000 0000', taxResidency=country, sourceOfWealth='Synthetic business ownership and investment income', pep=i == 0, consent=advanced, submittedBy='Relationship manager' if advanced else None, createdAt=now(), dueDate=date_after(due), reviewDate=date_after(180), kyc={key: advanced for key in CHECKS}, customFields={}, documents=[dict(id=f'seed-{i}-{j}', name=t.lower().replace(' ','-')+'.txt', type=t, status='Verified' if advanced else 'Pending review', size=128, uploadedAt=now(), sample=True) for j,t in enumerate(docs)], activity=[dict(id=str(uuid4()), at=now(), actor=owner, action=f'{stage} · Case updated', note='Synthetic data — not real client data')]))
    return migrate(db)

def migrate(db):
    """Import the prior Node JSON once without overwriting or deleting it."""
    db.setdefault('ui', default_ui())
    db.setdefault('workflow', default_workflow())
    db.setdefault('workflowVersions', {'1': deepcopy(db['workflow'])})
    db.setdefault('workflowDraft', deepcopy(db['workflow']))
    db.setdefault('draftRevision', 1)
    db.setdefault('revision', 0)
    db.setdefault('configAudit', [])
    for c in db['cases']:
        c.setdefault('workflowVersion', 1)
        c.setdefault('customFields', {})
        if c['stage'] in ['Active','Periodic review']: c.setdefault('activatedAt',c['createdAt'])
    for r in db['rules']:
        if 'conditions' not in r:
            field, op, value = {'High risk': ('risk','eq','High'), 'PEP': ('pep','eq',True), 'Entity': ('type','ne','Individual')}[r['condition']]
            r['conditions'] = dict(match='all', items=[dict(field=field, op=op, value=value)])
            r['documents'] = [r['document']]
            r['requiredFields'] = []
    return db
