"""Reusable presentation patterns; native widgets keep keyboard and mobile support."""
from datetime import date
from html import escape
import streamlit as st

STAGE_ICONS={'prospect':'person_add','documents':'folder_open','review':'fact_check','approval':'verified_user','active':'task_alt','closed':'archive','custom':'account_tree'}

def brand_logo(brand):
    # An SVG wordmark is an image, not an injected app stylesheet.
    name=escape(brand[:26])
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="340" height="54" viewBox="0 0 340 54"><rect width="44" height="44" y="5" rx="12" fill="#245eae"/><path d="M11 34L22 14L33 34M16 27H28" fill="none" stroke="white" stroke-width="2"/><text x="58" y="30" font-family="Georgia,serif" font-size="25" letter-spacing="3" fill="#193655">{name}</text><text x="59" y="47" font-family="Arial,sans-serif" font-size="8" letter-spacing="2" fill="#60748a">PRIVATE BANKING · CLIENT LIFECYCLE</text></svg>'

def header(eyebrow,title,subtitle):
    st.caption(eyebrow.upper())
    st.title(title)
    st.caption(subtitle)

def due_label(c):
    days=(date.fromisoformat(c['dueDate'])-date.today()).days
    if c['stageKind'] in ['active','closed']: return 'Relationship active' if c['stageKind']=='active' else 'Archived'
    return f'{abs(days)}d overdue' if days<0 else 'Due today' if days==0 else f'Due in {days}d'

def evidence(c):
    total=len(c['requiredDocuments'])
    verified=sum(any(d['type']==t and d['status']=='Verified' for d in c['documents']) for t in c['requiredDocuments'])
    return verified,total

def open_case(cid,section='Overview'):
    st.session_state['_open_case']=cid
    st.session_state[cid+'_section']=section
    st.switch_page('app_pages/cases.py')

def case_rows(cases,key,limit=None):
    if not cases:
        st.info('No relationships match these filters.',icon=':material/search:');return
    for c in cases[:limit] if limit else cases:
        with st.container(border=True,gap='xsmall'):
            a,b,d=st.columns([2.5,1.7,1.4],vertical_alignment='center')
            with a:
                st.markdown('**'+c['name']+'**')
                st.caption(c['id']+' · '+c['owner'])
            with b:
                st.badge(c['stage'],color='green' if c['stageKind']=='active' else 'blue')
                st.caption(c['risk']+' risk · '+due_label(c))
            with d:
                if st.button('Open case',key=f'{key}_{c["id"]}',icon=':material/arrow_forward:',width='stretch'):
                    open_case(c['id'])

def journey(stages,current=None,cases=None):
    if cases is not None:
        for col,s in zip(st.columns(len(stages),wrap=False),stages):
            with col:
                count=sum(c['stage']==s['name'] for c in cases)
                st.subheader(str(count),anchor=False)
                st.progress(count/max(1,len(cases)))
                st.caption(s['name'])
        return
    # Scrolls as one connected strip instead of wrapping into unrelated cards.
    with st.container(horizontal=True,wrap=False,gap='small'):
        for i,s in enumerate(stages):
            with st.container(border=True,width=155,gap='xsmall'):
                icon=STAGE_ICONS.get(s['kind'],'account_tree')
                st.caption(f'{i+1:02d}  ·  '+('CURRENT STAGE' if s['name']==current else s['owner']))
                st.markdown(f':material/{icon}: **{s["name"]}**')
                if cases is not None:
                    n=sum(c['stage']==s['name'] for c in cases)
                    st.caption(f'{n} '+('relationship' if n==1 else 'relationships'))
                elif s['name']==current: st.badge('You are here',color='blue')
                else: st.caption(f'{s["slaDays"]} day target')
