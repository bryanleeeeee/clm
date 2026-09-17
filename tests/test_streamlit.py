from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from clm.streamlit_support import flask_resource
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def ui(tmp_path,monkeypatch):
    monkeypatch.setenv('DATA_DIR',str(tmp_path));flask_resource.clear()
    app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=30).run()
    assert not app.exception
    return app

def test_navigation_and_synthetic_notice(ui):
    assert 'SYNTHETIC DATA' in ui.warning[0].value
    assert len(ui.metric)==5
    for path in ['cases','documents','workflows','policies','reports','settings']:
        ui.switch_page(f'app_pages/{path}.py').run()
        assert not ui.exception,path

def test_create_case_and_client_role(ui):
    ui.switch_page('app_pages/cases.py').run()
    next(x for x in ui.button if x.label=='New onboarding').click().run()
    next(x for x in ui.text_input if x.label=='Client / entity name').set_value('Streamlit Test')
    next(x for x in ui.text_input if x.label=='Email address').set_value('streamlit@example.com')
    next(x for x in ui.button if x.label=='Create onboarding').click().run()
    assert not ui.exception
    gateway=ui.session_state['_api'];data=gateway.request('/state')
    new=next(c for c in data['cases'] if c['name']=='Streamlit Test')
    ui.selectbox(key='portal_identity').select(new['id']).run()
    ui.selectbox(key='demo_role').select('Client').run()
    assert not ui.exception
    assert len(gateway.request('/state')['cases'])==1
    assert any(x.value=='Welcome to your onboarding' for x in ui.title)

def test_workflow_insert_save_and_publish(ui):
    ui.selectbox(key='demo_role').select('Compliance').run()
    ui.switch_page('app_pages/workflows.py').run()
    next(x for x in ui.text_input if x.label=='New stage name').set_value('Suitability review')
    # Insert into the documentation → due diligence route.
    next(x for x in ui.selectbox if x.label=='Insert into route').select('route-2')
    next(x for x in ui.button if x.label=='Insert stage').click().run()
    assert not ui.exception
    assert any(s['name']=='Suitability review' for s in ui.session_state['_workflow_edit']['stages'])
    next(x for x in ui.button if x.label=='Save draft').click().run()
    assert not ui.exception
    ui.segmented_control(key='workflow_workspace').set_value('Test & publish').run()
    next(x for x in ui.button if x.label=='Validate the draft').click().run()
    assert not ui.error
    next(x for x in ui.text_area if x.label=='What changed in this version?').set_value('Insert synthetic suitability review')
    next(x for x in ui.button if x.label=='Publish workflow').click().run()
    assert not ui.exception
    data=ui.session_state['_api'].request('/state')
    assert data['workflow']['version']==2
    assert all(c['workflowVersion']==1 for c in data['cases'])

def test_native_form_builder(ui):
    ui.selectbox(key='demo_role').select('Operations').run()
    ui.switch_page('app_pages/settings.py').run()
    next(x for x in ui.segmented_control if x.label=='Settings section').set_value('Form builder').run()
    next(x for x in ui.text_input if x.label=='Stable field key').set_value('investment_goal')
    next(x for x in ui.text_input if x.label=='Field label').set_value('Investment goal')
    next(x for x in ui.checkbox if x.label=='Required before approval').check()
    next(x for x in ui.button if x.label=='Save form field').click().run()
    assert not ui.exception
    data=ui.session_state['_api'].request('/state')
    assert data['ui']['customFields'][0]['key']=='investment_goal'
    ui.switch_page('app_pages/cases.py').run()
    next(x for x in ui.button if x.label=='Open case').click().run()
    next(x for x in ui.segmented_control if x.label=='Case section').set_value('Profile').run()
    assert any(x.label=='Investment goal *' for x in ui.text_input)
    assert not ui.exception

def test_dashboard_case_shortcuts_and_directory(ui):
    next(x for x in ui.button if x.label=='Open case').click().run()
    assert not ui.exception
    # AppTest needs its page hash synchronized after a programmatic switch.
    ui.switch_page('app_pages/cases.py').run()
    next(x for x in ui.button if x.label=='Upload & review documents').click().run()
    assert next(x for x in ui.segmented_control if x.label=='Case section').value=='Documents'
    next(x for x in ui.button if x.label=='All relationships').click().run()
    next(x for x in ui.segmented_control if x.label=='Workspace view').set_value('Pipeline board').run()
    assert not ui.exception
    next(x for x in ui.text_input if x.label=='Find a relationship').set_value('Isabelle').run()
    assert len([x for x in ui.button if x.label=='Open case'])==1
    next(x for x in ui.button if x.label=='Open case').click().run()
    assert not ui.exception
    assert any(x.value=='Isabelle Tan' for x in ui.subheader)


def test_dashboard_new_onboarding_dialog(ui):
    next(x for x in ui.button if x.label=='New onboarding').click().run()
    assert not ui.exception
    assert any(x.label=='Client / entity name' for x in ui.text_input)
    ui.switch_page('app_pages/cases.py').run()
    next(x for x in ui.text_input if x.label=='Client / entity name').set_value('Dashboard Demo')
    next(x for x in ui.text_input if x.label=='Email address').set_value('dashboard@example.com')
    next(x for x in ui.button if x.label=='Create onboarding').click().run()
    assert not ui.exception
    assert any(x.value=='Dashboard Demo' for x in ui.subheader)
