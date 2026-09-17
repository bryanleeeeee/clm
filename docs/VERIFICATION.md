# Verification — Python edition

Verified locally on Windows with Python 3.14.7, Streamlit 1.64.0 and Flask 3.1.3.

`python -m pytest tests -q`: **13 passed**.

Seven backend tests cover the complete onboarding-to-closure lifecycle, client isolation, upload validation and persisted bytes, document verification, due diligence, independent approval, periodic review resets, transactional rollback, configuration version pinning, stale-update rejection, migration, graph validation, custom fields, conditional policies, read-only simulation and synthetic notices.

Six Streamlit AppTest tests cover native page rendering, top synthetic notice, case creation and client-role isolation, inserting/saving/validating/publishing a workflow step, and required custom fields in the profile builder. Additional UI tests cover dashboard-to-case navigation, document shortcuts, directory search, pipeline selection and the new-onboarding dialog. Tests use temporary storage.

`python tests/browser_demo.py` checks running Streamlit at port 8501 and Flask at port 4176 with Microsoft Edge through Playwright. It checks native navigation, workflow designer rendering, Flask navigation, synthetic notices and JavaScript page errors; captures desktop/mobile screenshots under ignored `artifacts/`. Start both servers first. This script requires Microsoft Edge and the development requirements. The browser check passed locally.

The current tests do not certify production authentication, regulatory compliance, external integrations, load, accessibility or Cloudera tenant compatibility. Community Cloud deployment is performed by the repository owner; it has not been claimed as verified here.
