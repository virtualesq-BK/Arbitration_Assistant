"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/useApi";
import { formatMoney, humanize, type AgentResponse, type Claim, type EvidenceMatrix } from "@/lib/types";
import AIResponseCard from "@/components/AIResponseCard";
import { Badge, EmptyState, ErrorBox, Loading } from "@/components/ui";

const CLAIM_TYPES = ["EOT", "LD_DEFENCE", "VARIATION", "PAYMENT", "DISRUPTION", "SUSPENSION", "TERMINATION", "DEFECT", "OTHER"];

export default function ClaimsPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const { token } = useAuth();
  const { data: claims, error, loading, reload } = useApi<Claim[]>(`/cases/${caseId}/claims`);
  const { data: matrix, reload: reloadMatrix } = useApi<EvidenceMatrix>(`/cases/${caseId}/evidence-matrix`);

  const [analysis, setAnalysis] = useState<AgentResponse | null>(null);
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [ref, setRef] = useState("");
  const [type, setType] = useState("EOT");
  const [title, setTitle] = useState("");
  const [quantum, setQuantum] = useState("");
  const [clause, setClause] = useState("");

  async function analyzeClaim(claimId: string) {
    if (!token) return;
    setAnalyzingId(claimId);
    setActionError(null);
    try {
      setAnalysis(await apiFetch<AgentResponse>(`/cases/${caseId}/claims/${claimId}/analyze`, { method: "POST", token }));
    } catch (err: unknown) {
      setActionError(errorMessage(err));
    } finally {
      setAnalyzingId(null);
    }
  }

  async function createClaim(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!token) return;
    setActionError(null);
    try {
      await apiFetch<Claim>(`/cases/${caseId}/claims`, {
        method: "POST",
        token,
        body: JSON.stringify({ claim_ref: ref, claim_type: type, title, quantum: quantum || null, currency: quantum ? "USD" : null, contract_clause: clause || null }),
      });
      setShowForm(false);
      setRef("");
      setTitle("");
      setQuantum("");
      setClause("");
      reload();
      reloadMatrix();
    } catch (err: unknown) {
      setActionError(errorMessage(err));
    }
  }

  return (
    <div className="space-y-6">
      <section className="card overflow-x-auto p-0">
        <div className="flex items-center justify-between p-4">
          <h2 className="section-title mb-0">Claims {claims ? `(${claims.length})` : ""}</h2>
          <button type="button" className="btn-secondary" onClick={() => setShowForm((s) => !s)}>{showForm ? "Close" : "Add claim"}</button>
        </div>
        {showForm && (
          <form onSubmit={createClaim} className="grid gap-3 border-t border-slate-100 p-4 md:grid-cols-6">
            <input aria-label="Reference" className="input" placeholder="Ref e.g. EOT-03" value={ref} onChange={(e) => setRef(e.target.value)} required />
            <select aria-label="Type" className="input" value={type} onChange={(e) => setType(e.target.value)}>
              {CLAIM_TYPES.map((t) => <option key={t} value={t}>{humanize(t)}</option>)}
            </select>
            <input aria-label="Title" className="input md:col-span-2" placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
            <input aria-label="Quantum (USD)" className="input" placeholder="Quantum USD" value={quantum} onChange={(e) => setQuantum(e.target.value.replace(/[^0-9.]/g, ""))} />
            <input aria-label="Contract clause" className="input" placeholder="Clause" value={clause} onChange={(e) => setClause(e.target.value)} />
            <div className="md:col-span-6 flex justify-end"><button type="submit" className="btn-primary">Save claim</button></div>
          </form>
        )}
        <ErrorBox message={error ?? actionError} />
        {loading && <div className="px-4"><Loading /></div>}
        {claims && claims.length === 0 && <div className="p-4"><EmptyState>No claims recorded.</EmptyState></div>}
        {claims && claims.length > 0 && (
          <table className="table">
            <thead>
              <tr><th>Ref</th><th>Type</th><th>Title</th><th>Clause</th><th className="text-right">Quantum</th><th>Evidence</th><th>Status</th><th /></tr>
            </thead>
            <tbody>
              {claims.map((c) => (
                <tr key={c.id}>
                  <td className="font-mono text-xs font-semibold">{c.claim_ref}</td>
                  <td><Badge tone="blue">{humanize(c.claim_type)}</Badge></td>
                  <td>
                    <div className="font-medium">{c.title}</div>
                    {c.description && <div className="text-xs text-slate-500">{c.description}</div>}
                  </td>
                  <td className="text-xs">{c.contract_clause ?? "—"}</td>
                  <td className="whitespace-nowrap text-right tabular-nums">{formatMoney(c.quantum, c.currency)}</td>
                  <td>
                    <Link href={`/cases/${caseId}/evidence?claim=${c.id}`} className="text-brand-700 hover:underline">{c.evidence_count} docs</Link>
                  </td>
                  <td><Badge>{humanize(c.status)}</Badge></td>
                  <td>
                    <button type="button" className="btn-secondary px-2 py-1 text-xs" disabled={analyzingId !== null} onClick={() => analyzeClaim(c.id)}>
                      {analyzingId === c.id ? "Analysing…" : "AI analyse"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {analysis && <AIResponseCard response={analysis} caseId={caseId} />}

      <section className="card overflow-x-auto p-0">
        <div className="p-4">
          <h2 className="section-title mb-0">Claim–evidence matrix</h2>
          <p className="text-xs text-slate-500">Rows: documents linked to at least one claim. ● = linked (hover for relevance note).</p>
        </div>
        {!matrix ? (
          <div className="px-4"><Loading /></div>
        ) : matrix.rows.length === 0 ? (
          <div className="p-4"><EmptyState>No evidence links yet.</EmptyState></div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Date</th>
                {matrix.claims.map((c) => <th key={c.id} className="text-center">{c.claim_ref}</th>)}
              </tr>
            </thead>
            <tbody>
              {matrix.rows.map((r) => (
                <tr key={r.document_id}>
                  <td>
                    <Link href={`/cases/${caseId}/documents?doc=${r.document_id}`} className="text-brand-700 hover:underline">{r.filename}</Link>
                    <div className="text-xs text-slate-500">{humanize(r.document_type)} {r.evidence_number ? `· ${r.evidence_number}` : ""}</div>
                  </td>
                  <td className="whitespace-nowrap tabular-nums">{r.doc_date ?? "—"}</td>
                  {matrix.claims.map((c) => {
                    const note = r.claim_links[c.id];
                    return (
                      <td key={c.id} className="text-center" title={note ?? ""}>
                        {note !== undefined ? <span className="text-lg text-brand-600">●</span> : <span className="text-slate-200">·</span>}
                      </td>
                    );
                  })}
                </tr>
              ))}
              <tr className="bg-slate-50 font-medium">
                <td colSpan={2}>Linked documents</td>
                {matrix.claims.map((c) => <td key={c.id} className="text-center tabular-nums">{c.evidence_count}</td>)}
              </tr>
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
