// Mirrors of the FastAPI response schemas (apps/api/schemas).

export const INSTITUTIONS = ["ICC", "SIAC", "LCIA", "HKIAC", "ICDR"] as const;

export type FindingLabel =
  | "FACT"
  | "SOURCE_BASED_INFO"
  | "AI_SUMMARY"
  | "POTENTIAL_ISSUE"
  | "POTENTIAL_EVIDENCE_GAP"
  | "REQUIRES_HUMAN_REVIEW";

export interface Finding {
  label: FindingLabel;
  content: string;
  citations: string[];
}

export interface AgentSource {
  id: string;
  type: "case_document" | "rule" | "reference" | "case_record" | "timeline" | string;
  document_id?: string | null;
  filename?: string;
  document_type?: string;
  doc_date?: string | null;
  text?: string;
  source_name?: string;
  source_url?: string | null;
  institution?: string | null;
  rule_version?: string | null;
  chunk_index?: number | null;
  confidence?: number;
}

export interface AgentResponse {
  summary: string;
  findings: Finding[];
  evidence_gaps: string[];
  requires_human_review: string[];
  sources: AgentSource[];
  model: string;
  agent: string;
  disclaimer: string;
  analysis_id: string | null;
}

export interface CaseStats {
  documents: number;
  claims: number;
  timeline_events: number;
  issues: number;
  open_procedural_events: number;
}

export interface CaseParty {
  id: string;
  name: string;
  role: string;
  counsel: string | null;
  country: string | null;
}

export interface Case {
  id: string;
  org_id: string;
  title: string;
  description: string | null;
  institution: string;
  seat: string | null;
  governing_law: string | null;
  language: string;
  status: "ACTIVE" | "CLOSED" | "ARCHIVED";
  amount_in_dispute: string | null;
  currency: string | null;
  case_ref: string | null;
  created_at: string;
  updated_at: string;
  stats: CaseStats;
  parties?: CaseParty[];
}

export interface DocumentItem {
  id: string;
  case_id: string;
  filename: string;
  file_size: number | null;
  mime_type: string | null;
  document_type: string;
  author: string | null;
  recipient: string | null;
  doc_date: string | null;
  confidentiality_level: string;
  privilege_status: string;
  evidence_number: string | null;
  ocr_status: string;
  summary: string | null;
  created_at: string;
}

export interface DocumentDetail extends DocumentItem {
  ocr_text: string | null;
  download_url: string | null;
  download_url_expires_in: number | null;
  chunk_count: number;
}

export interface TimelineEvent {
  id: string;
  case_id: string;
  event_date: string;
  description: string;
  event_type: string;
  source_document_id: string | null;
  source_document_filename: string | null;
  source_page: number | null;
  source_excerpt: string | null;
  is_ai_extracted: boolean;
}

export interface Claim {
  id: string;
  case_id: string;
  claim_ref: string;
  claim_type: string;
  title: string;
  description: string | null;
  quantum: string | null;
  currency: string | null;
  status: string;
  contract_clause: string | null;
  evidence_count: number;
}

export interface ClaimEvidence {
  id: string;
  claim_id: string;
  document_id: string;
  relevance_note: string | null;
  added_by_ai: boolean;
  document_filename: string | null;
  document_type: string | null;
  document_date: string | null;
  evidence_number: string | null;
}

export interface EvidenceMatrixRow {
  document_id: string;
  filename: string;
  document_type: string;
  doc_date: string | null;
  evidence_number: string | null;
  claim_links: Record<string, string | null>;
}

export interface EvidenceMatrix {
  claims: Claim[];
  rows: EvidenceMatrixRow[];
}

export interface EvidenceGap {
  claim_id: string;
  claim_ref: string;
  claim_type: string;
  missing_document_types: string[];
  message: string;
}

export interface EvidenceOverview {
  evidence: ClaimEvidence[];
  gaps: EvidenceGap[];
  unlinked_documents: number;
}

export interface Issue {
  id: string;
  title: string;
  description: string | null;
  category: string | null;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  status: string;
}

export interface ProceduralEvent {
  id: string;
  case_id: string;
  event_type: string;
  title: string | null;
  due_date: string | null;
  source_rule: string | null;
  rule_reference: string | null;
  source_url: string | null;
  status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "OVERDUE" | "NOT_APPLICABLE";
  notes: string | null;
  is_ai_suggested: boolean;
  requires_confirmation: boolean;
}

export interface Institution {
  id: string;
  name: string;
  short_name: string;
  website: string | null;
  rules_version: string | null;
  rules_effective_date: string | null;
  rules_url: string | null;
  source_tier: string;
}

export interface Rule {
  id: string;
  institution_id: string;
  stage: string;
  article_number: string;
  title: string;
  summary: string;
  source_url: string | null;
  rule_version: string | null;
  notes: string | null;
  typical_deadline_days: number | null;
}

export interface ComparisonCell {
  article_number: string;
  title: string;
  source_url: string | null;
  rule_version: string | null;
}

export interface ComparisonTable {
  institutions: Institution[];
  rows: { stage: string; cells: Record<string, ComparisonCell[]> }[];
}

export interface ProcedureStageResponse {
  institution: Institution;
  stage: string;
  rules: Rule[];
  source_not_found: boolean;
  ai_guidance: AgentResponse | null;
  disclaimer: string;
}

export interface AnalysisListItem {
  id: string;
  agent: string;
  model_name: string;
  created_at: string;
  summary: string | null;
}

export interface AnalysisRecord {
  id: string;
  agent: string;
  model_name: string;
  created_at: string;
  query: string | null;
  output_json: AgentResponse | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  org_id: string;
}

export function humanize(value: string | null | undefined): string {
  if (!value) return "—";
  return value
    .toLowerCase()
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function formatMoney(amount: string | null, currency: string | null): string {
  if (amount === null || amount === undefined) return "—";
  const n = Number(amount);
  if (Number.isNaN(n)) return amount;
  return `${currency ?? ""} ${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`.trim();
}
