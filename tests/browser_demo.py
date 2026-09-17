from pathlib import Path
from playwright.sync_api import sync_playwright
import json, re
root=Path(__file__).resolve().parents[1];(root/'artifacts').mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1480,'height':1080})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8501');page.get_by_role('heading',name='Every relationship starts here.').wait_for(timeout=30000)
    page.locator('[data-testid="stMetricValue"]').first.wait_for();page.wait_for_timeout(1800)
    page.screenshot(path=str(root/'artifacts/streamlit-overview.png'),full_page=True)
    for name in ['Onboarding','Document centre','Workflows','Rules & policies','Reports & insights','UI & settings']:
        page.get_by_role('link',name=re.compile(re.escape(name)+'$')).click()
        page.wait_for_timeout(1500)
        assert page.locator('[data-testid="stException"]').count()==0,name
        if name=='Workflows':
            page.get_by_role('heading',name='Workflow studio').wait_for();page.screenshot(path=str(root/'artifacts/streamlit-workflow.png'),full_page=True)
    page.get_by_role('link',name=re.compile('Overview$')).click()
    page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(400);page.screenshot(path=str(root/'artifacts/streamlit-mobile.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1080})
    page.goto('http://127.0.0.1:4176');page.get_by_role('heading',name='Every relationship starts here.').wait_for()
    assert page.get_by_text('SYNTHETIC DATA — NOT REAL CLIENT DATA · Demonstration workspace only',exact=True).count()==1
    for name in ['Onboarding','Client directory','Document centre','Workflows','Rules & policies','Reports & insights']:
        page.locator('.nav-item').filter(has_text=name).first.click()
        assert page.locator('h1').count()==1
    page.locator('[data-page="Overview"]').first.click()
    page.screenshot(path=str(root/'artifacts/flask-overview.png'),full_page=True)
    assert errors==[],errors
    print('PASS: Streamlit navigation and workflow designer, desktop/mobile screenshots, Flask screens, synthetic notices, no page errors.')
    (root/'artifacts/browser-results.json').write_text(json.dumps({'passed':True,'errors':errors},indent=2))
    browser.close()
