"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/useApi";
import { humanize, type Case, type ProceduralEvent } from "@/lib/types";
import { Badge, EmptyState, ErrorBox, Loading, statusTone } from "@/components/ui";

const STATUSES: ProceduralEvent["status"][] = ["PENDING", "IN_PROGRESS", "COMPLETED", "OVERDUE", "NOT_APPLICABLE"];

export default function ProcedurePage() {
  const { caseId } = useParams<{ caseId: string }>();
  const { token } = useAuth();
  const { data: c } = useApi<Case>(`/cases/${caseId}`);
  const { data: events, error, loading, reload } = useApi<ProceduralEvent[]>(`/cases/${caseId}/procedure`);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function generate() {
    if (!token) return;
    setBusy(true);
    setActionError(null);
    try {
      await apiFetch<ProceduralEvent[]>(`/cases/${caseId}/procedure/generate`, { method: "POST", token });
      reload();
    } catch (err: unknown) {
      setActionError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function update(ev: ProceduralEvent, patch: Partial<Pick<ProceduralEvent, "status" | "requires_confirmation">>) {
    if (!token) return;
    setActionError(null);
    try {
      await apiFetch<ProceduralEvent>(`/cases/${caseId}/procedure/${ev.id}`, { method: "PATCH", token, body: JSON.stringify(patch) });
      reload();
    } catch (err: unknown) {
      setActionError(errorMessage(err));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="section-title mb-0">Procedural checklist</h2>
          <p className="text-xs text-slate-500">
            Steps are linked to {c?.institution ?? "institution"} rule citations. AI-suggested steps must be confirmed by a responsible lawyer; deadlines depend on the arbitration agreement and procedural orders.
          </p>
        </div>
        <button type="button" className="btn-secondary" onClick={generate} disabled={busy}>{busy ? "Generating…" : `Suggest steps from ${c?.institution ?? ""} rules`}</button>
      </div>
      <ErrorBox message={error ?? actionError} />
      {loading && <Loading />}
      {events && events.length === 0 && <EmptyState>No procedural steps yet — use “Suggest steps” to draft a checklist from seeded rules.</EmptyState>}
      {events && events.length > 0 && (
        <div className="card overflow-x-auto p-0">
          <table className="table">
            <thead>
              <tr><th>Done</th><th>Stage / step</th><th>Due</th><th>Source citation</th><th>Status</th><th>Notes</th></tr>
            </thead>
            <tbody>
              {events.map((ev) => (
                <tr key={ev.id} className={ev.requires_confirmation ? "bg-red-50/50" : ""}>
                  <td>
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-brand-600"
                      checked={ev.status === "COMPLETED"}
                      aria-label={`Mark ${ev.title ?? ev.event_type} complete`}
                      onChange={(e) => update(ev, { status: e.target.checked ? "COMPLETED" : "PENDING" })}
                    />
                  </td>
                  <td>
                    <div className="text-xs uppercase tracking-wide text-slate-500">{humanize(ev.event_type)}</div>
                    <div className="font-medium">{ev.title ?? "—"}</div>
                    {ev.is_ai_suggested && (
                      <div className="mt-1 flex items-center gap-2">
                        <Badge tone="purple">AI suggested</Badge>
                        {ev.requires_confirmation && (
                          <button type="button" className="text-xs font-medium text-red-700 underline" onClick={() => update(ev, { requires_confirmation: false })}>
                            ⚠ Confirm step
                          </button>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="whitespace-nowrap tabular-nums">{ev.due_date ?? "—"}</td>
                  <td className="text-sm">
                    {ev.source_url ? (
                      <a href={ev.source_url} target="_blank" rel="noreferrer" className="text-brand-700 underline underline-offset-2">
                        {ev.source_rule} {ev.rule_reference}
                      </a>
                    ) : ev.rule_reference ? (
                      <span>{ev.source_rule} {ev.rule_reference}</span>
                    ) : (
                      <span className="text-slate-400">Source not found.</span>
                    )}
                  </td>
                  <td>
                    <select
                      aria-label="Status"
                      className="rounded border border-slate-200 bg-white px-1 py-0.5 text-xs"
                      value={ev.status}
                      onChange={(e) => update(ev, { status: e.target.value as ProceduralEvent["status"] })}
                    >
                      {STATUSES.map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
                    </select>
                    <div className="mt-1"><Badge tone={statusTone(ev.status)}>{humanize(ev.status)}</Badge></div>
                  </td>
                  <td className="max-w-xs text-xs text-slate-600">{ev.notes ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
