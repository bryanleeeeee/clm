"""Declarative policies and a versioned workflow interpreter. No eval or code execution."""
import re
import math
from copy import deepcopy
from uuid import uuid4
from .defaults import BASE_DOCUMENTS, CHECKS, FIELDS, GUARDS, STAFF, KINDS, NAV, now, date_after

class ValidationError(ValueError):
    pass

def require(condition, message):
    if not condition:
        raise ValidationError(message)

def text(value, label, limit=200, optional=False):
    require(isinstance(value, str) and (optional or bool(value.strip())), f'{label} is required')
    require(len(value) <= limit, f'{label} exceeds {limit} characters')
    return value.strip()

def audit(db, actor, action, note=''):
    db['configAudit'].insert(0, dict(id=str(uuid4()), at=now(), actor=actor, action=action, note=note))

def event(c, actor, action, note=''):
    c['activity'].insert(0, dict(id=str(uuid4()), at=now(), actor=actor, action=action, note=note))

def workflow_for(c, db):
    return db['workflowVersions'][str(c['workflowVersion'])]

def stage_for(c, db, workflow=None):
    return next(s for s in (workflow or workflow_for(c, db))['stages'] if s['name'] == c['stage'])

def value_for(c, field):
    return c.get('customFields', {}).get(field[7:]) if field.startswith('custom.') else c.get(field)

def validate_conditions(group, ui):
    require(isinstance(group, dict) and group.get('match') in ['all', 'any'], 'Choose all or any conditions')
    items = group.get('items')
    require(isinstance(items, list) and len(items) <= 20, 'Use no more than 20 conditions')
    custom = {'custom.'+f['key']: f['type'] for f in ui['customFields']}
    for item in items:
        require(isinstance(item, dict), 'Invalid condition')
        field, op, value = item.get('field'), item.get('op'), item.get('value')
        require(field in FIELDS or field in custom, 'Unknown condition field')
        require(op in ['eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'contains'], 'Unknown condition operator')
        require(isinstance(value, (str, int, float, bool)) and len(str(value)) <= 500, 'Invalid condition value')
        if field == 'aum' or custom.get(field) == 'number' or op in ['gt','gte','lt','lte']:
            try:
                require(math.isfinite(float(value)), 'Condition number must be finite')
            except (ValueError, TypeError):
                raise ValidationError('Condition requires a number')
        if field == 'pep' or custom.get(field) == 'checkbox':
            require(op in ['eq','ne'] and (isinstance(value, bool) or value in ['true','false']), 'Checkbox conditions use equals/not equals and true/false')
    return deepcopy(group)

def matches(group, c):
    results = []
    for item in group['items']:
        current, op, expected = value_for(c, item['field']), item['op'], item['value']
        if current is None:
            results.append(False)
            continue
        if isinstance(current, bool):
            expected = expected is True or str(expected).lower() == 'true'
        if op in ['gt','gte','lt','lte']:
            try:
                a, b = float(current), float(expected)
                result = {'gt': a>b, 'gte': a>=b, 'lt': a<b, 'lte': a<=b}[op]
            except (ValueError,TypeError):
                result = False
        elif op == 'in':
            result = str(current).casefold() in [x.strip().casefold() for x in str(expected).split(',')]
        elif op == 'contains':
            result = str(expected).casefold() in str(current).casefold()
        else:
            if isinstance(current,(int,float)) and not isinstance(current,bool):
                try: expected=float(expected)
                except (ValueError,TypeError): pass
            result = str(current).casefold() == str(expected).casefold()
            if op == 'ne': result = not result
        results.append(result)
    return not results or (all(results) if group['match'] == 'all' else any(results))

def applicable_rules(c, db):
    return [r for r in db['rules'] if r['enabled'] and matches(r['conditions'], c)]

def requirements(c, db):
    result = list(BASE_DOCUMENTS)
    for r in applicable_rules(c, db):
        result.extend(r['documents'])
    return list(dict.fromkeys(result))

def required_fields(c, db):
    keys = [f['key'] for f in db['ui']['customFields'] if f['required']]
    for r in applicable_rules(c, db): keys.extend(r.get('requiredFields', []))
    return list(dict.fromkeys(keys))

def profile_issues(c, db):
    issues = []
    for key in ['email','residency','taxResidency','sourceOfWealth']:
        if not c.get(key): issues.append(f'Complete {key}')
    fields = {f['key']: f for f in db['ui']['customFields']}
    for key in required_fields(c, db):
        v = c.get('customFields',{}).get(key)
        if v is None or v == '' or (fields[key]['type']=='checkbox' and v is not True):
            issues.append(f'Complete {fields[key]["label"]}')
    return issues

def guard_issues(c, db, guards, actor, note='', workflow=None):
    docs = requirements(c, db)
    issues = []
    for gate in guards:
        if gate in ['documents_received','documents_verified']:
            for kind in docs:
                found = any(d['type']==kind and (d['status']=='Verified' if gate=='documents_verified' else d['status']!='Rejected') for d in c['documents'])
                if not found: issues.append(f'{kind} must be '+('verified' if gate=='documents_verified' else 'uploaded'))
        elif gate == 'profile_complete': issues.extend(profile_issues(c,db))
        elif gate == 'consent' and not c['consent']: issues.append('Client declaration is required')
        elif gate == 'kyc_complete': issues.extend(f'{label} review is incomplete' for key,label in CHECKS.items() if not c['kyc'].get(key))
        elif gate == 'independent_approval':
            if actor != 'Compliance': issues.append('Compliance approval is required')
            if not c.get('submittedBy') or c['submittedBy']==actor: issues.append('Approver must be independent of the submitting role')
        elif gate == 'reason' and len(note.strip())<8: issues.append('Provide a decision reason of at least 8 characters')
    return list(dict.fromkeys(issues))

def blockers(c, db):
    return guard_issues(c,db,['documents_verified','profile_complete','consent','kyc_complete'],'Compliance')

def mandatory_guards(target, source):
    if target['kind']=='approval': return ['documents_verified','profile_complete','consent','kyc_complete']
    if target['kind']=='active':
        gates=['documents_verified','profile_complete','consent','kyc_complete']
        if source['kind']!='review': gates.append('independent_approval')
        return gates
    if target['kind']=='closed': return ['reason']
    return []

def validate_workflow(w, ui):
    require(isinstance(w,dict), 'Workflow must be an object')
    text(w.get('name'), 'Workflow name', 120)
    stages, routes = w.get('stages'), w.get('transitions')
    require(isinstance(stages,list) and 2<=len(stages)<=30, 'A workflow needs 2–30 stages')
    require(isinstance(routes,list) and 1<=len(routes)<=120, 'A workflow needs 1–120 routes')
    names=[]
    for s in stages:
        text(s.get('name'), 'Stage name', 60)
        require(s['name'] not in names, 'Stage names must be unique')
        names.append(s['name'])
        require(s.get('kind') in KINDS and s.get('owner') in STAFF, 'Choose a valid stage type and owner')
        require(type(s.get('slaDays')) is int and 1<=s['slaDays']<=365, 'Stage target must be 1–365 days')
        require(type(s.get('editable')) is bool, 'Specify stage editability')
        require(s['kind'] not in ['approval','active','closed'] or not s['editable'], 'Approval, active and closed stages must be locked')
        text(s.get('description',''), 'Stage description',500,True)
    require(w.get('startStage') in names, 'Select a valid starting stage')
    stage_map={s['name']:s for s in stages}
    require(stage_map[w['startStage']]['kind'] in ['prospect','documents','custom'], 'Start in prospect, documentation or a custom stage')
    require(any(s['kind']=='active' for s in stages) and any(s['kind']=='closed' for s in stages), 'Include an active stage and a closed stage')
    seen=set()
    for r in routes:
        text(r.get('id'), 'Route ID',80)
        require(re.fullmatch(r'[A-Za-z0-9-]+',r['id']) and r['id'] not in seen, 'Route IDs must be unique alphanumeric identifiers')
        seen.add(r['id'])
        text(r.get('label'), 'Action label',80)
        require(r.get('source') in names and r.get('target') in names and r['source']!=r['target'], 'Routes must connect two distinct existing stages')
        source,target=stage_map[r['source']],stage_map[r['target']]
        require(source['kind']!='closed', 'Closed stages cannot have outgoing routes')
        require(isinstance(r.get('roles'),list) and r['roles'] and all(x in STAFF for x in r['roles']), 'Select at least one staff role')
        require(isinstance(r.get('guards'),list) and all(g in GUARDS for g in r['guards']), 'Invalid route gate')
        require(type(r.get('resetChecks')) is bool, 'Specify whether checks reset')
        require(not r['resetChecks'] or target['kind'] not in ['active','approval','closed'], 'Reset checks only when entering a working stage')
        required=mandatory_guards(target,source)
        require(all(g in r['guards'] for g in required), f'{r["label"]}: missing mandatory gates: '+', '.join(g for g in required if g not in r['guards']))
        if target['kind'] in ['active','closed']:
            require(r['roles']==['Compliance'], 'Activation and closure routes must be Compliance-only')
        if target['kind']=='active' and source['kind']=='review':
            require(r.get('conditions',{}).get('items') is not None, 'Configure route conditions')
        if source['kind']=='active' and target['kind']!='closed': require(r['resetChecks'], 'Leaving active for review must reset due diligence checks')
        validate_conditions(r.get('conditions'),ui)
    # Every stage must be reachable from the starting point (prospect is an optional entry stage).
    reached={w['startStage']} | {s['name'] for s in stages if s['kind']=='prospect'}
    while True:
        more=reached | {r['target'] for r in routes if r['source'] in reached}
        if more==reached: break
        reached=more
    require(set(names)==reached, 'Unreachable stages: '+', '.join(set(names)-reached))
    for s in stages:
        if s['kind']!='closed': require(any(r['source']==s['name'] for r in routes), f'{s["name"]} needs an outgoing route')
    # Every stage has a path to a closed endpoint, even when review cycles exist.
    finishing={s['name'] for s in stages if s['kind']=='closed'}
    while True:
        more=finishing | {r['source'] for r in routes if r['target'] in finishing}
        if more==finishing: break
        finishing=more
    require(set(names)==finishing, 'Every stage needs a path to closure')
    return deepcopy(w)

def validate_rules(rules, ui):
    require(isinstance(rules,list) and len(rules)<=50,'Use up to 50 policies')
    keys={f['key'] for f in ui['customFields']}
    ids=set()
    for r in rules:
        text(r.get('name'),'Rule name',120)
        require(type(r.get('enabled')) is bool,'Rule enabled must be true/false')
        require(re.fullmatch(r'[A-Za-z0-9-]{1,80}',r.get('id','')) and r['id'] not in ids,'Rule IDs must be unique')
        ids.add(r['id'])
        validate_conditions(r.get('conditions'),ui)
        require(isinstance(r.get('documents'),list) and len(r['documents'])<=15, 'Use up to 15 document requirements per rule')
        for d in r['documents']: text(d,'Document category',100)
        require(isinstance(r.get('requiredFields'),list) and all(k in keys for k in r['requiredFields']),'Unknown required form field')
        require(r['documents'] or r['requiredFields'],'A rule must require a document or form field')
        text(r.get('description',''),'Rule description',500,True)
    return deepcopy(rules)

def validate_ui(ui, db):
    text(ui.get('brand'),'Brand',30);text(ui.get('heading'),'Dashboard heading',120);text(ui.get('subtitle'),'Dashboard subtitle',250)
    require(re.fullmatch(r'#[0-9a-fA-F]{6}',ui.get('accent','')) is not None,'Choose a valid colour')
    require(ui.get('density') in ['comfortable','compact'],'Choose a valid density')
    require(isinstance(ui.get('navigation'),list) and all(n in NAV for n in ui['navigation']),'Invalid navigation')
    require(all(n in ui['navigation'] for n in ['Overview','Onboarding','Workflows','Rules & policies']), 'Overview, Onboarding, Workflows and Rules must remain accessible')
    require(isinstance(ui.get('dashboardCards'),list) and ui['dashboardCards'] and all(c in ['open','approval','attention','assets'] for c in ui['dashboardCards']),'Select at least one dashboard card')
    require(isinstance(ui.get('customFields'),list) and len(ui['customFields'])<=30,'Use up to 30 custom form fields')
    keys=set()
    for f in ui['customFields']:
        require(re.fullmatch(r'[a-z][a-z0-9_]{1,39}',f.get('key','')) and f['key'] not in keys,'Unique field keys must use lowercase letters, numbers or underscores')
        keys.add(f['key']);text(f.get('label'),'Field label',80)
        require(f.get('type') in ['text','textarea','number','date','select','checkbox'],'Invalid field type')
        require(type(f.get('required')) is bool and type(f.get('clientEditable')) is bool,'Choose field requirement and client editability')
        require(isinstance(f.get('options'),list) and len(f['options'])<=50,'Invalid field choices')
        if f['type']=='select': require(bool(f['options']),'Select fields need choices')
        for option in f['options']: text(option,'Option',100)
        old=next((x for x in db['ui']['customFields'] if x['key']==f['key']),None)
        if old and any(f['key'] in c.get('customFields',{}) for c in db['cases']): require(old['type']==f['type'],'Cannot change the type of a field with saved values')
    # Never silently break published routes or policy references by deleting a field.
    validate_rules(db['rules'], ui)
    for w in list(db['workflowVersions'].values())+[db['workflowDraft']]:
        for r in w['transitions']: validate_conditions(r['conditions'],ui)
    return deepcopy(ui)

def execute(c, db, action, actor, note=''):
    w=workflow_for(c,db)
    routes=[r for r in w['transitions'] if r['source']==c['stage'] and (r['id']==action or r['label']==action) and matches(r['conditions'],c)]
    require(len(routes)==1,'Choose an unambiguous available route; conditions may not match')
    route=routes[0]
    require(actor in route['roles'], 'This route requires: '+', '.join(route['roles']))
    source=stage_for(c,db)
    target=next(s for s in w['stages'] if s['name']==route['target'])
    gates=list(dict.fromkeys(route['guards']+mandatory_guards(target,source)))
    if target['kind']=='active' and source['kind']=='review':
        require(c.get('activatedAt'), 'A review cannot bypass first-time independent approval')
    issues=guard_issues(c,db,gates,actor,note)
    require(not issues,'; '.join(issues))
    if target['kind']=='approval': c['submittedBy']=actor
    if route['resetChecks']: c['kyc']={k:False for k in CHECKS}
    c['stage']=target['name'];c['dueDate']=date_after(target['slaDays'])
    if target['kind']=='active':
        c.setdefault('activatedAt', now());c['reviewDate']=date_after(365)
    event(c,actor,route['label'],note)
    return c

def case_view(c, db, actor):
    result=deepcopy(c);w=workflow_for(c,db);stage=stage_for(c,db)
    result.update(requiredDocuments=requirements(c,db),requiredFields=required_fields(c,db),blockers=blockers(c,db),editable=stage['editable'],stageKind=stage['kind'],canReview=stage['kind']=='review',workflowDefinition=w)
    result['availableActions']=[dict(id=r['id'],label=r['label'],target=r['target'],roles=r['roles'],allowed=actor in r['roles'],guards=r['guards'],issues=guard_issues(c,db,r['guards'],actor)) for r in w['transitions'] if r['source']==c['stage'] and matches(r['conditions'],c)]
    return result
