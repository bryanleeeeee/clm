# Verification â€” Python edition

Verified locally on Windows with Python 3.14.7, Streamlit 1.64.0 and Flask 3.1.3.

`python -m pytest tests -q`: **13 passed**.

Seven backend tests cover the complete onboarding-to-closure lifecycle, client isolation, upload validation and persisted bytes, document verification, due diligence, independent approval, periodic review resets, transactional rollback, configuration version pinning, stale-update rejection, migration, graph validation, custom fields, conditional policies, read-only simulation and synthetic notices.

Six Streamlit AppTest tests cover native page rendering, top synthetic notice, case creation and client-role isolation, inserting/saving/validating/publishing a workflow step, and required custom fields in the profile builder. Additional UI tests cover dashboard-to-case navigation, document shortcuts, directory search, pipeline selection and the new-onboarding dialog. Tests use temporary storage.

`python tests/browser_demo.py` checks running Streamlit at port 8501 and Flask at port 4176 with Microsoft Edge through Playwright. It checks native navigation, workflow designer rendering, Flask navigation, synthetic notices and JavaScript page errors; captures desktop/mobile screenshots under ignored `artifacts/`. Start both servers first. This script requires Microsoft Edge and the development requirements. The browser check passed locally.

The current tests do not certify production authentication, regulatory compliance, external integrations, load, accessibility or Cloudera tenant compatibility. Community Cloud deployment is performed by the repository owner; it has not been claimed as verified here.

## Vercel and durable storage

- The dedicated PostgreSQL integration test passed: a second application instance reads persisted case/file content; failed writes roll back state and files together; four concurrent writers retain all changes. It creates and removes only its own randomly named test schema.
- The public Vercel API completed one synthetic onboarding journey: client isolation, required-evidence gate, four PDF uploads, document reviews, four due diligence attestations, independent activation, exact-byte download, archival and a fresh-session persistence check. The archived `Aurelia Demo Verification` case is retained as demonstration evidence.
- Browser inspection confirmed the live original Aurelia dashboard at `bankclm.vercel.app` and its mobile layout. An isolated browser workspace verified inserting and validating a workflow step and saving a required custom profile field through the new guided editors.
- The Streamlit deployment was opened and its new grouped navigation, case queues, priorities and branded interface confirmed on the public URL.

`python scripts/check_postgres.py` runs the opt-in storage test using the ignored deployment environment. `python scripts/verify_deployment.py` explicitly creates and archives another synthetic case on the public demo; it is not part of the routine unit suite.

## SOW and work queue enhancement — September 2026
- Full suite: **26 passed, 1 skipped** (the opt-in PostgreSQL test). PostgreSQL integration run separately: **1 passed**.
- Additional coverage: partial financial corroboration, overlapping evidence, event-change invalidation, narrative-body citations, escaped HTML reports, client task isolation, staff ownership, response acceptance and stale revisions.
- Browser verification in isolated local data: assigned a client follow-up, submitted a client response, accepted it as staff, and confirmed retained history; inspected the evidence coverage matrix and report link.
