"""Case follow-ups and client requests. Portal submissions require staff acceptance."""
from datetime import date
from uuid import uuid4
from flask import jsonify, session
from .defaults import ROLES, now
from .domain import require, text, event, stage_for


def visible_tasks(c, actor):
    return [t for t in c.get('tasks',[]) if actor!='Client' or t['owner']=='Client']


def register_tasks(app, store, body, get_case, staff):
    @app.post('/api/cases/<identifier>/tasks')
    def create(identifier):
        staff();b=body()
        title=text(b.get('title'),'Task title',160)
        detail=text(b.get('detail',''),'Instructions',3000,True)
        require(b.get('owner') in ROLES,'Choose a valid assignee role')
        require(b.get('priority') in ['Normal','High'],'Choose a priority')
        require(b.get('category') in ['General','Documents','Source of wealth','Review'],'Choose a category')
        due=text(b.get('dueDate'),'Due date',10)
        try: date.fromisoformat(due)
        except ValueError: require(False,'Enter a valid due date')
        require(due>=date.today().isoformat(),'A new task cannot be due in the past')
        with store.transaction(True) as (db,_):
            c=get_case(db,identifier);require(stage_for(c,db)['kind']!='closed','Closed cases are read-only')
            tasks=c.setdefault('tasks',[]);require(len(tasks)<200,'Maximum 200 follow-ups per case')
            require(not any(t['title']==title and t['owner']==b['owner'] and t['status']!='Completed' for t in tasks),'An open task with this title and assignee already exists')
            task=dict(id=str(uuid4()),title=title,detail=detail,owner=b['owner'],priority=b['priority'],category=b['category'],dueDate=due,status='Open',revision=1,createdAt=now(),createdBy=session['role'],history=[])
            tasks.insert(0,task);event(c,session['role'],'Follow-up created',title+' · '+b['owner'])
        return jsonify(task),201

    @app.patch('/api/cases/<identifier>/tasks/<task_id>')
    def update(identifier,task_id):
        b=body();action=b.get('action');note=text(b.get('note'),'Response / rationale',3000)
        require(action in ['submit','complete','reopen'],'Choose a valid task action')
        with store.transaction(True) as (db,_):
            c=get_case(db,identifier);require(stage_for(c,db)['kind']!='closed','Closed cases are read-only')
            t=next((x for x in visible_tasks(c,session['role']) if x['id']==task_id),None)
            require(t is not None,'Task not found')
            require(b.get('revision')==t['revision'],'This task changed; reload before saving')
            if session['role']=='Client':
                require(action=='submit' and t['owner']=='Client' and t['status']=='Open','Clients can respond only to their open requests')
            else:
                require(action!='submit','Staff accept or reopen work; client submits responses')
                require(session['role']==t['owner'] or t['owner']=='Client' and session['role'] in ['Relationship manager','Operations','Compliance'],'The assigned role must complete this task')
                require(t['status']!='Completed' if action=='complete' else t['status']!='Open','Task already has this status')
            t['status']={'submit':'Submitted','complete':'Completed','reopen':'Open'}[action]
            t['revision']+=1;t['updatedAt']=now()
            t['history'].append(dict(at=now(),actor=session['role'],action=action,note=note))
            event(c,session['role'],'Follow-up '+t['status'].lower(),t['title']+': '+note)
        return jsonify(ok=True)
