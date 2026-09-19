# Source of Wealth workspace

Synthetic demonstration only. Open **Source of wealth** in the Vercel app, or **Open wealth assessment** in a client case.

## Guided demonstration
1. As Relationship manager, select an editable case. Record total net worth (SGD units), occupation, background, outflows and opening funds separately from assets under management.
2. Add chronological wealth events: original currency, manually sourced FX rate, beneficial ownership, costs/taxes and economic explanation. Use net gains and do not double-count reinvested principal.
3. Upload source documents in the case document vault under **Source of wealth evidence**, or cite a public source URL. Link the exact excerpt and page/section to one or more events. Client statements are distinguished from independent corroboration.
4. Operations or Compliance reviews evidence and uploaded documents. Placeholder sample documents do not count toward verified coverage. Historical sources need a relevance rationale after the configured age threshold.
5. Check reconciliation and material-source coverage. High-risk/PEP cases have an enhanced threshold and require rationale. Click a finding to reach its editor.
6. Prepare a cited write-up and edit it as needed. This is deterministic template assistance, not generative AI or automated factual validation. Changes to facts or evidence clear an unchanged old narrative.
7. Submit to Compliance. The submitted content locks. Compliance approves with rationale or requests changes. Each decision retains a full dossier snapshot; archived records are retained in the JSON review pack.
8. Complete case-level wealth KYC attestation during Due diligence, then request case approval through the normal independent approval workflow.

## Controls and compatibility
New cases created through the Flask/Vercel API require an approved dossier. Existing cases keep their prior flow until a dossier is started. Once started, the dossier gate applies at both case submission and activation. Case-level KYC cannot bypass it. Periodic review reopens the dossier. Profile risk changes, document status changes, policy changes and expired usable evidence invalidate the approval. Review consistency is protected by content fingerprints, role checks, atomic storage transactions and per-dossier optimistic revisions.

Compliance can change **Review thresholds** in the wealth register. Defaults are demonstration parameters: 80% standard coverage, 100% enhanced coverage, 10% materiality, 10% reconciliation tolerance, 365-day evidence relevance prompt. These are not regulatory standards or a probability of legitimacy. Old transactions can be supported by historical evidence with documented relevance. Coverage is the proportion of net wealth contributions with at least one independently corroborating, reviewed source; reviewers must assess whether each source supports the full claim.

The existing demo role switch is not authentication. No live screening, OSINT crawler, OCR, LLM or external benchmark data is connected. Public-source facts and documents require human inspection. FX rates are manually recorded with their basis. No automatic legitimacy conclusion or investment advice is produced. Native Streamlit remains a separate interface; this new dossier editor is in the Flask/Vercel interface.

## Design references
- [Bank of Singapore, Accelerating compliance transformation with Generative AI](https://www.bankofsingapore.com/research/accelerating-compliance-transformation-with-generative-ai.html): informs consistent report structure, explicit citations and human oversight. Its AI implementation is not replicated or implied in this demonstration.
- [smartKYC, Source of Wealth verification guide](https://smartkyc.com/source-of-wealth-verification-guide/): informs chronological events, separate source-of-funds capture, independent corroboration and documented review rationale.

## Verification
Run `python -m pytest tests -q`. `python scripts/check_postgres.py` runs the opt-in integration check in an isolated randomly named schema, verifying dossier decision snapshots across application instances alongside file persistence, rollback and concurrent writes.
