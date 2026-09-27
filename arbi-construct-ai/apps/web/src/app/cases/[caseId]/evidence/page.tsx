"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/useApi";
import { humanize, type AgentResponse, type Claim, type EvidenceOverview } from "@/lib/types";
import AIResponseCard from "@/components/AIResponseCard";
import { Badge, EmptyState, ErrorBox, Loading } from "@/components/ui";

function EvidenceInner() {
  const { caseId } = useParams<{ caseId: string }>();
  const search = useSearchParams();
  const { token } = useAuth();
  const { data, error, loading } = useApi<EvidenceOverview>(`/cases/${caseId}/evidence`);
  const { data: claims } = useApi<Claim[]>(`/cases/${caseId}/claims`);
  const [claimFilter, setClaimFilter] = useState<string>(search.get("claim") ?? "");
  const [analysis, setAnalysis] = useState<AgentResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const claimRef = useMemo(() => new Map((claims ?? []).map((c) => [c.id, c.claim_ref])), [claims]);
  const rows = (data?.evidence ?? []).filter((e) => !claimFilter || e.claim_id === claimFilter);
  const gaps = (data?.gaps ?? []).filter((g) => !claimFilter || g.claim_id === claimFilter);

  async function runEvidenceAgent() {
    if (!token) return;
    setBusy(true);
    setAiError(null);
    try {
      setAnalysis(await apiFetch<AgentResponse>(`/cases/${caseId}/evidence/analyze`, { method: "POST", token }));
    } catch (err: unknown) {
      setAiError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <ErrorBox message={error} />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <label htmlFor="claimf" className="text-sm text-slate-600">Claim</label>
          <select id="claimf" className="input w-auto" value={claimFilter} onChange={(e) => setClaimFilter(e.target.value)}>
            <option value="">All claims</option>
            {(claims ?? []).map((c) => <option key={c.id} value={c.id}>{c.claim_ref} — {c.title}</option>)}
          </select>
        </div>
        <button type="button" className="btn-primary" onClick={runEvidenceAgent} disabled={busy}>{busy ? "Running Evidence Agent…" : "Run Evidence Agent"}</button>
      </div>

      <section>
        <h2 className="section-title">Potential evidence gaps</h2>
        {gaps.length === 0 ? (
          <EmptyState>No rule-based evidence gaps detected{claimFilter ? " for this claim" : ""}.</EmptyState>
        ) : (
          <ul className="space-y-2">
            {gaps.map((g) => (
              <li key={g.claim_id} className="rounded-md border border-amber-300 bg-yellow-50 p-3 text-sm text-amber-900">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-semibold">{g.claim_ref}</span>
                  <Badge tone="yellow">POTENTIAL EVIDENCE GAP</Badge>
                  {g.missing_document_types.map((t) => <Badge key={t} tone="yellow">missing: {humanize(t)}</Badge>)}
                </div>
                <p>{g.message}</p>
              </li>
            ))}
          </ul>
        )}
        {data && data.unlinked_documents > 0 && (
          <p className="mt-2 text-xs text-slate-500">{data.unlinked_documents} case documents are not linked to any claim.</p>
        )}
      </section>

      <section className="card overflow-x-auto p-0">
        <h2 className="section-title p-4 pb-0">Linked evidence ({rows.length})</h2>
        {rows.length === 0 ? (
          <div className="p-4"><EmptyState>No evidence linked.</EmptyState></div>
        ) : (
          <table className="table mt-3">
            <thead>
              <tr><th>Claim</th><th>Exhibit</th><th>Document</th><th>Type</th><th>Date</th><th>Relevance note</th><th>Source</th></tr>
            </thead>
            <tbody>
              {rows.map((e) => (
                <tr key={e.id}>
                  <td className="font-mono text-xs font-semibold">{claimRef.get(e.claim_id) ?? "—"}</td>
                  <td className="text-xs">{e.evidence_number ?? "—"}</td>
                  <td><Link href={`/cases/${caseId}/documents?doc=${e.document_id}`} className="text-brand-700 hover:underline">{e.document_filename}</Link></td>
                  <td>{humanize(e.document_type)}</td>
                  <td className="whitespace-nowrap tabular-nums">{e.document_date ?? "—"}</td>
                  <td className="text-slate-600">{e.relevance_note ?? "—"}</td>
                  <td>{e.added_by_ai ? <Badge tone="purple">AI suggested</Badge> : <Badge>User</Badge>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <ErrorBox message={aiError} />
      {analysis && <AIResponseCard response={analysis} caseId={caseId} />}
    </div>
  );
}

export default function EvidencePage() {
  return (
    <Suspense fallback={<Loading />}>
      <EvidenceInner />
    </Suspense>
  );
}
