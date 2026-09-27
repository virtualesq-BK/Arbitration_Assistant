# ArbiConstruct AI — Legal Product Boundary

> Status: **internal working draft for counsel review.** This document was prepared by the product
> team to frame issues. It is not legal advice, and none of its conclusions should be relied on
> until qualified counsel in each relevant jurisdiction has reviewed them.

ArbiConstruct AI is a **software tool** that helps qualified lawyers, in-house legal teams and
claims professionals organise documents, chronologies, claims and procedural steps in
international construction arbitrations. It does **not** provide legal advice or legal
representation. Every section below uses the same structure:

**Issue | Relevant Rule | Product Risk | Recommended Control | Requires Counsel Review**

---

## 1. Korean Attorney-at-Law Act (변호사법)

| Field | Detail |
|---|---|
| **Issue** | Whether offering AI-generated analysis of disputes to paying users amounts to a non-lawyer handling legal affairs (법률사무) or brokering legal services. |
| **Relevant Rule** | Attorney-at-Law Act Art. 109 (non-lawyers handling legal affairs, such as giving legal opinions or drafting legal documents on specific cases for compensation); Art. 34 (brokering / fee-sharing with non-lawyers); Korean Bar Association guidance and past disputes about legal-tech platforms. |
| **Product Risk** | If outputs read as case-specific legal opinions ("the claim is time-barred") given to non-lawyer customers for a fee, regulators or the Bar could treat the service as unauthorised legal practice. Marketing that says "AI lawyer" makes this more likely. |
| **Recommended Control** | Position and contract the product as a **software licence** for information management and research. Sell to law firms, in-house legal departments and claims teams working under qualified lawyers. Ban "AI lawyer" and "legal advice" wording from marketing. Build in the product controls listed in §3. Do not introduce customers to lawyers for referral fees. |
| **Requires Counsel Review** | **YES** — Korean counsel to confirm the positioning, the terms of service and the marketing copy before commercial launch in Korea. |

## 2. Unauthorised practice of law (other jurisdictions)

| Field | Detail |
|---|---|
| **Issue** | Seat and user jurisdictions (Singapore, England & Wales, Hong Kong, US states) regulate who may give legal advice and represent parties in arbitration. |
| **Relevant Rule** | For example: Singapore Legal Profession Act (the Part IXA regime for foreign representation in international arbitration); England & Wales Legal Services Act 2007 (reserved legal activities); US state UPL statutes. |
| **Product Risk** | The product could be seen as substituting for counsel when it is used by claims teams without lawyer supervision. |
| **Recommended Control** | The system **assists** qualified lawyers and claims teams; it is not a substitute for them. Terms of service require customers to have qualified legal professionals review outputs before relying on them. Role-based access (ORG_ADMIN, LAWYER, CLAIMS_TEAM, ...) lets firms restrict AI features to supervised users. |
| **Requires Counsel Review** | **YES** — for each launch market. |

## 3. Product controls that enforce the boundary

| Field | Detail |
|---|---|
| **Issue** | How the boundary is enforced in the software itself, not only in the contract. |
| **Relevant Rule** | Internal policy (CLAUDE.md "AI Product Boundary"); professional-conduct duties of the supervising lawyers. |
| **Product Risk** | AI output that predicts outcomes or states legal conclusions, or that cites rules that do not exist. |
| **Recommended Control** | (a) Every finding carries a label: `FACT`, `SOURCE_BASED_INFO`, `AI_SUMMARY`, `POTENTIAL_ISSUE`, `POTENTIAL_EVIDENCE_GAP` or `REQUIRES_HUMAN_REVIEW`. (b) `legal_safety_validator` removes outcome predictions, probability estimates ("70% chance") and advice phrasing ("I advise you to"), replaces them with a `REQUIRES_HUMAN_REVIEW` marker and logs a warning. (c) `citation_validator` flags any article or rule number that does not appear in the retrieved sources. (d) The prompt forbids outcome predictions and requires "Source not found." when no source supports a statement. (e) AI-suggested procedural steps are stored with `requires_confirmation = true` until a human confirms them. (f) Every AI call is audited (the `ai_analyses` table stores the prompt version, retrieved sources and output). (g) A disclaimer is shown on every AI output and in the page footer. |
| **Requires Counsel Review** | **YES** — confirm that these controls, and the disclaimer wording, are adequate. |

## 4. Privacy: GDPR and the Korean Personal Information Protection Act (개인정보 보호법)

| Field | Detail |
|---|---|
| **Issue** | Case files contain personal data: witness names, employee records, correspondence, and sometimes health or safety incident data. |
| **Relevant Rule** | GDPR Arts. 5, 6, 9, 28 (processor terms), 32 (security) and 35 (DPIA); PIPA Arts. 15 and 17 (collection and provision to third parties), Art. 26 (entrustment of processing), Art. 29 (safety measures); Singapore PDPA; Hong Kong PDPO. |
| **Product Risk** | The platform processes personal data on the customer's behalf and needs a lawful basis and a clear controller/processor allocation. The risks are over-collection and retention beyond what the arbitration needs. |
| **Recommended Control** | Customer is the controller and ArbiConstruct is the processor/entrustee, under a DPA or entrustment agreement. Case data is isolated by tenant (org_id / case_id filters enforced in the retrieval layer, with tests). Access control and audit logs are in place. Retention and deletion policies are set per case (archive, then purge). A DPIA is carried out before launch. Adding PII redaction before LLM calls is on the roadmap. |
| **Requires Counsel Review** | **YES** |

## 5. International data transfer (LLM API calls)

| Field | Detail |
|---|---|
| **Issue** | AI features send document excerpts to an external, OpenAI-compatible LLM gateway (`OPENAI_BASE_URL`). That gateway and its upstream model providers may process the data outside the customer's jurisdiction. |
| **Relevant Rule** | GDPR Chapter V (Arts. 44–49: SCCs and transfer impact assessments); PIPA Art. 28-8 (overseas transfer of personal information) and Art. 26 (entrustment disclosure); contractual confidentiality duties under the arbitration agreement and institutional rules (e.g. LCIA Art. 30, SIAC Rule 39). |
| **Product Risk** | Confidential arbitration material and personal data cross borders. The provider could retain data or use it for training. |
| **Recommended Control** | Disclose the LLM sub-processors and their locations. Use providers that do not train on customer data and offer zero or limited retention. Offer a per-organisation setting to switch AI off or to use a regional or self-hosted model. Send only the retrieved excerpts, never whole files. Log every call in `ai_analyses`. Keep the embeddings and database in the customer's chosen region. **Note:** in the current MVP every AI call goes to the configured gateway. |
| **Requires Counsel Review** | **YES** |

## 6. Attorney–client privilege and without-prejudice material

| Field | Detail |
|---|---|
| **Issue** | Privileged documents (legal advice, work product, draft expert reports) and without-prejudice correspondence can be uploaded alongside disclosable documents. |
| **Relevant Rule** | Legal advice and litigation privilege under English law; IBA Rules on the Taking of Evidence Art. 9.2(b) (and Art. 9.4 in the 2020 edition); the Korean Attorney-at-Law Act Art. 26 confidentiality duty (Korea has no general common-law-style privilege). The applicable privilege rules in an arbitration are themselves contested. |
| **Product Risk** | Privileged material is exposed during document production, or waiver is argued because privileged content was shared with a third-party AI provider. |
| **Recommended Control** | `privilege_status` and `confidentiality_level` are **classified by users**. The AI may only flag text as **"POTENTIALLY_PRIVILEGED"**, labelled `REQUIRES_HUMAN_REVIEW`; it never decides privilege. Planned: exclude documents marked `PRIVILEGED` / `ATTORNEY_WORK_PRODUCT` from AI calls by default, and restrict their visibility by role. |
| **Requires Counsel Review** | **YES** — especially whether sending privileged content to an LLM provider risks waiver in each relevant jurisdiction. |

## 7. AI output disclaimer requirements

| Field | Detail |
|---|---|
| **Issue** | Users and third parties must understand that outputs are AI-generated, may be wrong, and are not legal advice. |
| **Relevant Rule** | Consumer protection and unfair-terms law; the EU AI Act transparency obligations (Art. 50) where applicable; Korea's Framework Act on AI (AI 기본법) transparency and notice duties for generative AI (in force from January 2026; confirm the scope and the implementing decrees). |
| **Product Risk** | Users over-rely on the output. A disclaimer that is not shown where the output is displayed may not be effective. |
| **Recommended Control** | Standing footer: *"ArbiConstruct AI provides AI-assisted information management and research. It does not provide legal advice or legal representation. AI outputs must be reviewed by qualified legal professionals."* On every AI card: *"AI-assisted analysis. Final legal judgment must be performed by qualified legal professionals."* Label AI-extracted and AI-suggested items in the UI. Keep the disclaimer in exported reports (roadmap). |
| **Requires Counsel Review** | **YES** |

## 8. Required legal review items before commercial launch

| Field | Detail |
|---|---|
| **Issue** | A consolidated checklist of legal reviews that must be complete before paid launch. |
| **Relevant Rule** | All of the above. |
| **Product Risk** | Launching without these reviews exposes the company and its customers to regulatory, professional-conduct and contractual risk. |
| **Recommended Control** | 1. Korean Attorney-at-Law Act opinion on the positioning, pricing model and marketing (§1). 2. UPL review for each launch market (§2). 3. Terms of service, acceptable use policy and customer-supervision covenant. 4. DPA / entrustment agreement, sub-processor list and DPIA (§4). 5. Cross-border transfer mechanism and LLM vendor contract review, including no-training and retention terms (§5). 6. Privilege-handling policy and default exclusion of privileged documents from AI processing (§6). 7. Disclaimer wording and placement, plus AI Act / Framework Act on AI transparency review (§7). 8. Accuracy of the seeded institutional-rule summaries against official texts (the SIAC Rules 2025 and other rule updates). 9. Security review: penetration test, key management, audit-log retention. 10. Professional indemnity / tech E&O insurance. |
| **Requires Counsel Review** | **YES** |
