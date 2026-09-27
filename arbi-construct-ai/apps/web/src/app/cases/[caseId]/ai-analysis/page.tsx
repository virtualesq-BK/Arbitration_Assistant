"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/useApi";
import type { AgentResponse, AnalysisListItem, AnalysisRecord } from "@/lib/types";
import AIResponseCard, { FindingBadge } from "@/components/AIResponseCard";
import { EmptyState, ErrorBox, Loading } from "@/components/ui";

export default function AIAnalysisPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const { token } = useAuth();
  const { data: history, reload } = useApi<AnalysisListItem[]>(`/cases/${caseId}/analyses`);
  const [current, setCurrent] = useState<AgentResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedId || !token) return;
    apiFetch<AnalysisRecord>(`/analyses/${selectedId}`, { token })
      .then((rec) => {
        if (rec.output_json) setCurrent({ ...rec.output_json, analysis_id: rec.id, disclaimer: rec.output_json.disclaimer ?? "" });
      })
      .catch((e: unknown) => setError(errorMessage(e)));
  }, [selectedId, token]);

  async function run() {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const res = await apiFetch<AgentResponse>(`/cases/${caseId}/analyze`, { method: "POST", token });
      setCurrent(res);
      setSelectedId(null);
      reload();
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-4">
      <div className="space-y-4 lg:col-span-3">
        <div className="card flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="section-title mb-1">Case Intelligence Agent</h2>
            <p className="text-sm text-slate-500">
              Generates a labelled briefing from the case record, chronology, claims, evidence links and institution rules. Every run is audited.
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {(["FACT", "SOURCE_BASED_INFO", "AI_SUMMARY", "POTENTIAL_ISSUE", "POTENTIAL_EVIDENCE_GAP", "REQUIRES_HUMAN_REVIEW"] as const).map((l) => (
                <FindingBadge key={l} label={l} />
              ))}
            </div>
          </div>
          <button type="button" className="btn-primary" onClick={run} disabled={busy}>{busy ? "Analysing case…" : "Run case analysis"}</button>
        </div>
        <ErrorBox message={error} />
        {busy && <Loading label="The agent is gathering sources and drafting the briefing (this can take up to a minute)…" />}
        {current ? <AIResponseCard response={current} caseId={caseId} /> : !busy && <EmptyState>Run an analysis or open one from the history.</EmptyState>}
      </div>

      <aside className="card h-fit">
        <h3 className="section-title">History</h3>
        {!history ? (
          <Loading />
        ) : history.length === 0 ? (
          <p className="text-sm text-slate-500">No analyses yet.</p>
        ) : (
          <ul className="space-y-2">
            {history.map((h) => (
              <li key={h.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(h.id)}
                  className={`w-full rounded-md border px-3 py-2 text-left text-sm hover:border-brand-500 ${selectedId === h.id ? "border-brand-500 bg-brand-50" : "border-slate-200"}`}
                >
                  <div className="font-medium">{h.agent}</div>
                  <div className="text-xs text-slate-500">{new Date(h.created_at).toLocaleString()}</div>
                  {h.summary && <div className="mt-1 line-clamp-2 text-xs text-slate-600">{h.summary}</div>}
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>
    </div>
  );
}
