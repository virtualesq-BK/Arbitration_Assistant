"use client";

import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState, type FormEvent } from "react";
import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/useApi";
import { humanize, type AgentResponse, type DocumentDetail, type DocumentItem } from "@/lib/types";
import AIResponseCard from "@/components/AIResponseCard";
import { Badge, EmptyState, ErrorBox, Loading, type Tone } from "@/components/ui";

const DOC_TYPES = [
  "CONTRACT", "AMENDMENT", "VARIATION_ORDER", "NOTICE", "LETTER", "EMAIL", "MEETING_MINUTES", "DAILY_REPORT",
  "PROGRAMME", "PAYMENT_CERTIFICATE", "INVOICE", "CHANGE_ORDER", "SITE_INSTRUCTION", "TECHNICAL_REPORT",
  "EXPERT_REPORT", "WITNESS_STATEMENT", "PHOTOGRAPH", "DRAWING", "SPECIFICATION", "CLAIM_SUBMISSION", "RESPONSE",
  "ARBITRATION_FILING", "PROCEDURAL_ORDER", "AWARD", "OTHER",
];
const CONFIDENTIALITY = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "HIGHLY_CONFIDENTIAL", "PRIVILEGED", "ATTORNEY_WORK_PRODUCT"];

function confidentialityTone(level: string): Tone {
  if (level === "PRIVILEGED" || level === "ATTORNEY_WORK_PRODUCT") return "purple";
  if (level === "HIGHLY_CONFIDENTIAL") return "red";
  if (level === "CONFIDENTIAL") return "yellow";
  return "slate";
}

function DocumentsInner() {
  const { caseId } = useParams<{ caseId: string }>();
  const search = useSearchParams();
  const { token } = useAuth();
  const [filter, setFilter] = useState("");
  const listPath = `/cases/${caseId}/documents${filter ? `?document_type=${filter}` : ""}`;
  const { data: docs, error, loading, reload } = useApi<DocumentItem[]>(listPath);

  const fileRef = useRef<HTMLInputElement>(null);
  const [docType, setDocType] = useState("OTHER");
  const [docDate, setDocDate] = useState("");
  const [author, setAuthor] = useState("");
  const [confidentiality, setConfidentiality] = useState("CONFIDENTIAL");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(search.get("doc"));
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [analysis, setAnalysis] = useState<AgentResponse | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedId || !token) return;
    setDetail(null);
    setAnalysis(null);
    setDetailError(null);
    apiFetch<DocumentDetail>(`/documents/${selectedId}`, { token })
      .then(setDetail)
      .catch((e: unknown) => setDetailError(errorMessage(e)));
  }, [selectedId, token]);

  async function onUpload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file || !token) return;
    const form = new FormData();
    form.append("file", file);
    form.append("document_type", docType);
    form.append("confidentiality_level", confidentiality);
    if (docDate) form.append("doc_date", docDate);
    if (author) form.append("author", author);
    setUploading(true);
    setUploadError(null);
    try {
      await apiFetch<DocumentItem>(`/cases/${caseId}/documents`, { method: "POST", token, body: form });
      if (fileRef.current) fileRef.current.value = "";
      setAuthor("");
      setDocDate("");
      reload();
    } catch (err: unknown) {
      setUploadError(errorMessage(err));
    } finally {
      setUploading(false);
    }
  }

  async function analyze(kind: "analyze" | "contract-analyze") {
    if (!selectedId || !token) return;
    setAnalyzing(true);
    setDetailError(null);
    try {
      setAnalysis(await apiFetch<AgentResponse>(`/documents/${selectedId}/${kind}`, { method: "POST", token }));
    } catch (err: unknown) {
      setDetailError(errorMessage(err));
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={onUpload} className="card">
        <h2 className="section-title">Upload document</h2>
        <div className="grid gap-3 md:grid-cols-6">
          <div className="md:col-span-2">
            <label htmlFor="file" className="label">File (PDF, TXT, EML…)</label>
            <input id="file" ref={fileRef} type="file" className="block w-full text-sm file:mr-3 file:rounded file:border-0 file:bg-brand-50 file:px-3 file:py-2 file:text-brand-700" required />
          </div>
          <div>
            <label htmlFor="dtype" className="label">Type</label>
            <select id="dtype" className="input" value={docType} onChange={(e) => setDocType(e.target.value)}>
              {DOC_TYPES.map((t) => <option key={t} value={t}>{humanize(t)}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="ddate" className="label">Date</label>
            <input id="ddate" type="date" className="input" value={docDate} onChange={(e) => setDocDate(e.target.value)} />
          </div>
          <div>
            <label htmlFor="author" className="label">Author</label>
            <input id="author" className="input" value={author} onChange={(e) => setAuthor(e.target.value)} />
          </div>
          <div>
            <label htmlFor="conf" className="label">Confidentiality</label>
            <select id="conf" className="input" value={confidentiality} onChange={(e) => setConfidentiality(e.target.value)}>
              {CONFIDENTIALITY.map((t) => <option key={t} value={t}>{humanize(t)}</option>)}
            </select>
          </div>
        </div>
        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="text-xs text-slate-500">Uploaded text is chunked and indexed for this case only. Privilege status is set by users; the AI only flags “potentially privileged”.</p>
          <button type="submit" className="btn-primary" disabled={uploading}>{uploading ? "Uploading…" : "Upload"}</button>
        </div>
        <div className="mt-3"><ErrorBox message={uploadError} /></div>
      </form>

      <div className="grid gap-6 xl:grid-cols-5">
        <section className="card overflow-x-auto p-0 xl:col-span-3">
          <div className="flex items-center justify-between gap-3 p-4">
            <h2 className="section-title mb-0">Documents {docs ? `(${docs.length})` : ""}</h2>
            <select aria-label="Filter by type" className="input w-auto" value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="">All types</option>
              {DOC_TYPES.map((t) => <option key={t} value={t}>{humanize(t)}</option>)}
            </select>
          </div>
          <ErrorBox message={error} />
          {loading && <div className="px-4"><Loading /></div>}
          {docs && docs.length === 0 && <div className="p-4"><EmptyState>No documents.</EmptyState></div>}
          {docs && docs.length > 0 && (
            <table className="table">
              <thead>
                <tr><th>Filename</th><th>Type</th><th>Date</th><th>Author</th><th>Confidentiality</th></tr>
              </thead>
              <tbody>
                {docs.map((d) => (
                  <tr key={d.id} onClick={() => setSelectedId(d.id)} className={`cursor-pointer hover:bg-slate-50 ${selectedId === d.id ? "bg-brand-50" : ""}`}>
                    <td className="font-medium text-brand-700">
                      {d.filename}
                      {d.evidence_number && <span className="ml-2 text-xs text-slate-400">{d.evidence_number}</span>}
                    </td>
                    <td>{humanize(d.document_type)}</td>
                    <td className="whitespace-nowrap tabular-nums">{d.doc_date ?? "—"}</td>
                    <td className="max-w-[180px] truncate" title={d.author ?? ""}>{d.author ?? "—"}</td>
                    <td><Badge tone={confidentialityTone(d.confidentiality_level)}>{humanize(d.confidentiality_level)}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="space-y-4 xl:col-span-2">
          {!selectedId && <EmptyState>Select a document to view its text and run AI analysis.</EmptyState>}
          <ErrorBox message={detailError} />
          {selectedId && !detail && !detailError && <Loading />}
          {detail && (
            <div className="card space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold">{detail.filename}</h3>
                  <p className="text-xs text-slate-500">
                    {humanize(detail.document_type)} · {detail.doc_date ?? "undated"} · {detail.chunk_count} indexed chunks
                  </p>
                </div>
                {detail.download_url && (
                  <a href={detail.download_url} className="btn-secondary text-xs" title={`Link expires in ${detail.download_url_expires_in}s`}>Download</a>
                )}
              </div>
              {detail.summary && <p className="rounded bg-slate-50 p-2 text-sm text-slate-700">{detail.summary}</p>}
              <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-700">
                {detail.ocr_text ?? "No extracted text available."}
              </pre>
              <div className="flex gap-2">
                <button type="button" className="btn-primary" disabled={analyzing} onClick={() => analyze("analyze")}>{analyzing ? "Analysing…" : "Analyse document"}</button>
                {(detail.document_type === "CONTRACT" || detail.document_type === "AMENDMENT") && (
                  <button type="button" className="btn-secondary" disabled={analyzing} onClick={() => analyze("contract-analyze")}>Contract review</button>
                )}
              </div>
            </div>
          )}
          {analysis && <AIResponseCard response={analysis} caseId={caseId} />}
        </section>
      </div>
    </div>
  );
}

export default function DocumentsPage() {
  return (
    <Suspense fallback={<Loading />}>
      <DocumentsInner />
    </Suspense>
  );
}
