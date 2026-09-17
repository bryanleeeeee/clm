# Aurelia · Private Banking CLM

**SYNTHETIC DATA — NOT REAL CLIENT DATA.** A working demonstration of configurable private banking onboarding and lifecycle management, designed for Singapore and SGD reporting.

Native **Python + Streamlit** is the default interface. An optional Flask interface is included. Both use the same Python validation, workflow engine and transactional SQLite document storage. Hosting does not require Node.js or npm. The optional Flask browser interface retains HTML, CSS and browser JavaScript; it is not a Python-rendered UI.

## Deploy on Streamlit Community Cloud

At https://share.streamlit.io/deploy use:

| Setting | Value |
| --- | --- |
| Repository | `bryanleeeeee/clm` |
| Branch | `main` |
| Main file path | `streamlit_app.py` |
| Python | `3.14` (locally tested) |

Dependencies install from `requirements.txt`. No secrets or external services are required for the synthetic demo. The first launch creates fictional cases automatically. All visitors share the demonstration database; the role selector is intentionally a demo simulator.

**Community Cloud local storage is not guaranteed to persist.** Cases, uploads and configuration can reset on a restart/redeploy. Export configuration before making substantial changes. Use durable database/object storage before using this beyond a synthetic demonstration. See [Streamlit storage guidance](https://docs.streamlit.io/develop/concepts/connections/connecting-to-data).

## Run locally

From `C:\code\clm` in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Open http://localhost:8501. Optional Flask interface:

```powershell
.\.venv\Scripts\python.exe app.py
```

Flask uses Waitress at http://localhost:4173. Set `PORT` to select another port. Both interfaces share `data/aurelia.sqlite3` by default; set `DATA_DIR` to choose an alternative directory. Existing legacy `data/db.json` and referenced uploads are imported once when a new SQLite database is created. Local data and secrets are excluded from Git.

## Cloudera AI / Machine Learning Application

1. Create a Python project from this repository and install `requirements.txt` in its runtime.
2. Create an Application with script `launch_cloudera.py` for Streamlit, or `launch_flask_cloudera.py` for Flask.
3. The launchers bind to `0.0.0.0` and the platform-provided `CDSW_APP_PORT`.
4. Set `DATA_DIR` to a writable persistent project directory. Use one application instance with this SQLite implementation.

Python 3.14 is tested locally. Validate dependencies against your selected Cloudera Python runtime. The launchers are supplied but have not been executed inside your Cloudera tenant. See [Cloudera application port guidance](https://docs.cloudera.com/machine-learning/1.5.2/projects/topics/ml-embedded-web-apps.html).

## Demo walkthrough

1. **Relationship manager → New onboarding:** create a fictional individual or entity and complete their profile.
2. Expand **Client portal preview** in the sidebar, select the case under **Client portal identity**, switch to **Client**, and upload account forms and required PDF/JPEG/PNG evidence (10 MB maximum per document).
3. Switch to **Operations** or **Compliance** to verify each required document with notes.
4. Advance the case to review; **Compliance** records identity, screening, source-of-wealth and tax checks.
5. A **Relationship manager** submits for approval. **Compliance** independently activates the relationship. Unmet requirements block progression.
6. Start periodic review or close the relationship with a reason. Review resets due diligence. Dashboards, reports, document registers and case histories reflect the updates.

The controls distinguish received evidence from verified evidence. Upload bytes persist in SQLite; file signatures, file size, permissions and lifecycle gates are checked in Python.

## Workspace experience

The overview includes direct case access, approval/attention queues and deadline priorities. Onboarding offers a searchable relationship list and a horizontal pipeline board, stage/risk filters, and a focused creation dialog. Each case has an evidence checklist, document/profile shortcuts, a lifecycle journey and role-aware next actions. The document register opens the selected case directly into its review workspace. Navigation is grouped into Workspace and Design & governance.

## Configure without writing code

- **Workflows → Design journey:** edit stage owners and service targets, insert a step into an existing route, reorder the visual journey, or remove a step and its routes.
- **Configure routes:** choose source/destination, action label, roles, mandatory gates, conditional routing and review resets. Routes, rather than visual order alone, define execution.
- **Test & publish:** simulate a case and see blockers without moving it. Save a draft, validate graph reachability and controls, then publish as Compliance with a change note.
- Existing cases stay pinned to their published workflow version. Explicit migration supports compatible stages and resets checks where appropriate. Version history and configuration audit records remain available.
- **Rules & policies:** combine AND/OR conditions on risk, residence, assets, PEP, client type or custom fields; require additional documents and profile fields; preview affected cases.
- **UI & settings:** configure branding, dashboard cards, navigation and custom profile fields. Fields support text, number, date, checkbox and selection, required status and client editability.
- Streamlit native widget colours come from `.streamlit/config.toml`. Settings provides a downloadable theme file; replacing it requires a restart. The configured accent also drives charts; Flask applies its configured appearance directly.
- Configuration export contains workflow versions, rules and UI settings, without case data or credentials. The import action intentionally imports a **workflow draft only**, for validation before publication.

## Source layout

| Path | Responsibility |
| --- | --- |
| `streamlit_app.py`, `app_pages/` | Native Streamlit navigation and screens |
| `clm/streamlit_case.py`, `clm/streamlit_support.py` | Reusable case widgets and per-session service adapter |
| `clm/domain.py` | Policies, workflow validation, guards and transitions |
| `clm/web.py` | Flask API, role restrictions, upload handling and configuration services |
| `clm/store.py`, `clm/defaults.py` | Atomic persistence, migration and synthetic seed |
| `public/` | Optional Flask browser presentation |
| `tests/` | Isolated service, lifecycle and Streamlit tests |

Streamlit calls the Flask WSGI application in-process with a separate cookie jar per Streamlit session. There is no second server or iframe to configure on Community Cloud.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests -q
```

See [verification](docs/VERIFICATION.md) and [vendor research](docs/RESEARCH.md).

## Demonstration boundary

This is an end-to-end synthetic workflow demonstration, not a production banking system. Role switching is not authentication; independent approval currently separates roles rather than authenticated people. External screening, OCR, electronic signatures and account provisioning are not connected. Before real-client use, implement bank SSO and user entitlements, independent-person approvals, durable managed storage, malware scanning, encryption/key management, immutable audit retention, monitoring and bank-approved regulatory policies. Sample Singapore controls are not a regulatory compliance certification.
