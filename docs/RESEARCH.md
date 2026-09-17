# Research and product design

Research conducted 16–17 September 2026 using public vendor materials. These are vendor-described capabilities; no proprietary product, paid environment, or customer data was accessed. Aurelia uses an original design rather than reproducing a vendor interface.

| Reference | Observed product emphasis | Applied in Aurelia |
| --- | --- | --- |
| [Fenergo Client Lifecycle Management](https://www.fenergo.com/client-lifecycle-management) | Policy-driven onboarding, KYC, central reusable client data, beneficial ownership and ongoing lifecycle journeys | Central client record; conditional evidence requirements; review gates; linked documents and history; periodic review and offboarding |
| [Fenergo Working with Journeys](https://docs.fenergox.com/user-guides/essential-fenergo-saas-user-guides/working-with-journeys/working-with-journeys) | Explicit journeys and journey configuration | Visible stages, case queues and a published workflow reference |
| [Wealth Dynamix: What is Client Lifecycle Management?](https://wealth-dynamix.com/wp-content/uploads/2020/06/eBook-What-is-Client-Lifecycle-Management.pdf) | Connected, tracked workflows across departments | Separate relationship manager, Operations and Compliance perspectives; shared case history and ownership |
| [Wealth Dynamix: Managing the Client Lifecycle](https://www.wealth-dynamix.com/wp-content/uploads/2021/05/Managing-the-Client-Lifecycle-Research-Report_Final.pdf) | A client relationship view spanning engagement, onboarding and ongoing relationship management | Searchable client directory, indicative assets, manager workload and case-level relationship summary |
| [InvestCloud Client Solutions](https://investcloud.com/what-we-do/front-office-solutions/client-solutions/) | Guided client journeys, checklists and a client-facing document vault | Client checklist, profile capture, document upload and review status |
| [InvestCloud Advisor Solutions](https://investcloud.com/advisor-solutions/) | Unified client information, automated lifecycle workflows and ongoing servicing | Connected operational dashboard, pipeline board and lifecycle reports |

## Product decisions

**Two experiences on one case.** Staff need queue-level controls, evidence and decision history. Clients need clear requirements and progress. The portal and staff workspace share persisted records while the server restricts a client session to its assigned case.

**Progress is evidence-based.** Uploading is not verification. Required categories can be missing, received/pending or verified. The dashboard divides verified required categories by all required categories. Optional duplicate files do not inflate readiness.

**Decisions are explicit.** Document review and due diligence need written notes. Cases cannot request approval or activate with unmet requirements. The submitting role cannot also approve activation. This models a production separation-of-duties requirement; production must implement independent user identities and delegated entitlements.

**Configuration stays understandable.** The policy studio expresses condition → required evidence. Core requirements remain present; rules add evidence for high risk, PEP or legal entities. Live impact counts show the effect of changing a rule.

**A restrained private banking visual language.** White surfaces, pale blue backgrounds, navy serif page headings, small purposeful icons and muted status colours give the workspace a calm hierarchy. Labels accompany colour. Case details use a focused dialog; the portal has fewer actions and direct upload guidance. Responsive layouts preserve horizontal table scrolling inside its container.

**Singapore as operating context.** Booking centre and reporting currency default to Singapore and SGD. Country of residence, tax residency, source of wealth, PEP and beneficial-ownership evidence are included as sample controls. The MAS Notice 626 page was unavailable during this research; no current MAS rule interpretation is asserted. Regulatory configuration needs a separately validated policy source and bank approval.

## Deliberately separate integration work

The vendor platforms describe extensive automation and integrations. Aurelia does not claim to perform automatic sanctions checks, adverse-media searches, OCR, identity verification, electronic signatures, regulatory interpretation or bank-account provisioning. Its UI identifies disconnected integrations, and due diligence is a recorded human review. Production deployment requires the integrations and controls described in the README.
