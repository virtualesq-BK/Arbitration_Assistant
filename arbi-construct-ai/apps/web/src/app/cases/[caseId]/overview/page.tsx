"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useApi } from "@/lib/useApi";
import {
  formatMoney,
  humanize,
  type AnalysisListItem,
  type AnalysisRecord,
  type Case,
  type EvidenceOverview,
  type Issue,
  type ProceduralEvent,
} from "@/lib/types";
import { Badge, EmptyState, ErrorBox, Loading, severityTone, statusTone } from "@/components/ui";
import { AI_DISCLAIMER } from "@/components/AIResponseCard";

function isOverdue(ev: ProceduralEvent): boolean {
  if (!ev.due_date || ev.status === "COMPLETED" || ev.status === "NOT_APPLICABLE") return false;
  return new Date(ev.due_date) < new Date(new Date().toDateString());
}

export default function OverviewPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const { data: c, error, loading } = useApi<Case>(`/cases/${caseId}`);
  const { data: procedure } = useApi<ProceduralEvent[]>(`/cases/${caseId}/procedure`);
  const { data: issues } = useApi<Issue[]>(`/cases/${caseId}/issues`);
  const { data: evidence } = useApi<EvidenceOverview>(`/cases/${caseId}/evidence`);
  const { data: analyses } = useApi<AnalysisListItem[]>(`/cases/${caseId}/analyses`);
  const latestId = analyses && analyses.length > 0 ? analyses[0].id : null;
  const { data: latest } = useApi<AnalysisRecord>(latestId ? `/analyses/${latestId}` : null);

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  if (!c) return null;

  const overdue = (procedure ?? []).filter(isOverdue);
  const needsConfirmation = (procedure ?? []).filter((p) => p.requires_confirmation);
  const reviewItems = latest?.output_json?.requires_human_review ?? [];

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <section className="card">
          <h2 className="section-title">Case metadata</h2>
          <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
            {[
              ["Institution", c.institution],
              ["Seat", c.seat ?? "—"],
              ["Governing law", c.governing_law ?? "—"],
              ["Language", c.language],
              ["Amount in dispute", formatMoney(c.amount_in_dispute, c.currency)],
              ["Status", c.status],
              ["Reference", c.case_ref ?? "—"],
              ["Documents / claims", `${c.stats.documents} / ${c.stats.claims}`],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="text-xs uppercase tracking-wide text-slate-500">{k}</dt>
                <dd className="font-medium text-slate-900">{v}</dd>
              </div>
            ))}
          </dl>
          {c.description && <p className="mt-4 text-sm text-slate-600">{c.description}</p>}
          {c.parties && c.parties.length > 0 && (
            <div className="mt-4">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Parties</h3>
              <ul className="flex flex-wrap gap-2">
                {c.parties.map((p) => (
                  <li key={p.id} className="rounded-md border border-slate-200 px-3 py-1.5 text-sm">
                    <span className="font-medium">{p.name}</span> <Badge tone="blue">{humanize(p.role)}</Badge>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <section className="card">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="section-title mb-0">Procedure checklist</h2>
            <Link href={`/cases/${caseId}/procedure`} className="text-sm text-brand-700 hover:underline">Open procedure →</Link>
          </div>
          {!procedure ? (
            <Loading />
          ) : procedure.length === 0 ? (
            <EmptyState>No procedural steps yet. Generate a checklist from the institution rules on the Procedure tab.</EmptyState>
          ) : (
            <ul className="divide-y divide-slate-100">
              {procedure.map((p) => (
                <li key={p.id} className="flex items-start gap-3 py-2 text-sm">
                  <input type="checkbox" readOnly checked={p.status === "COMPLETED"} className="mt-1 h-4 w-4 accent-brand-600" aria-label={p.title ?? p.event_type} />
                  <div className="flex-1">
                    <div className="font-medium text-slate-800">{p.title ?? humanize(p.event_type)}</div>
                    <div className="text-xs text-slate-500">
                      {p.source_rule} {p.rule_reference}
                      {p.due_date && ` · due ${p.due_date}`}
                    </div>
                  </div>
                  {isOverdue(p) ? <Badge tone="red">Overdue</Badge> : <Badge tone={statusTone(p.status)}>{humanize(p.status)}</Badge>}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card">
          <h2 className="section-title">Issues</h2>
          {!issues ? (
            <Loading />
          ) : issues.length === 0 ? (
            <EmptyState>No issues recorded.</EmptyState>
          ) : (
            <ul className="space-y-3">
              {issues.map((i) => (
                <li key={i.id} className="rounded-md border border-slate-200 p-3">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{i.title}</span>
                    <Badge tone={severityTone(i.severity)}>{i.severity}</Badge>
                    {i.category && <Badge>{i.category}</Badge>}
                  </div>
                  {i.description && <p className="mt-1 text-sm text-slate-600">{i.description}</p>}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <aside className="space-y-6">
        <section className="card border-red-200">
          <h2 className="section-title flex items-center gap-2"><span aria-hidden="true">⚠</span> AI alerts</h2>
          <ul className="space-y-2 text-sm">
            {overdue.map((p) => (
              <li key={p.id} className="rounded-md bg-red-50 px-3 py-2 text-red-800">
                Overdue: {p.title ?? humanize(p.event_type)} (due {p.due_date})
              </li>
            ))}
            {needsConfirmation.map((p) => (
              <li key={p.id} className="rounded-md bg-red-50 px-3 py-2 text-red-800">
                ⚠ Confirm AI-suggested step: {p.title ?? humanize(p.event_type)}
              </li>
            ))}
            {(evidence?.gaps ?? []).map((g) => (
              <li key={g.claim_id} className="rounded-md bg-amber-50 px-3 py-2 text-amber-900">
                Potential evidence gap — {g.claim_ref}: {g.missing_document_types.map(humanize).join(", ") || "no linked evidence"}
              </li>
            ))}
            {reviewItems.slice(0, 5).map((r, i) => (
              <li key={`r${i}`} className="rounded-md bg-red-50 px-3 py-2 text-red-800">⚠ {r}</li>
            ))}
            {overdue.length + needsConfirmation.length + (evidence?.gaps.length ?? 0) + reviewItems.length === 0 && (
              <li className="text-slate-500">No alerts.</li>
            )}
          </ul>
          {latest && (
            <p className="mt-3 text-xs text-slate-500">
              Latest analysis: {latest.agent} · {new Date(latest.created_at).toLocaleString()} ·{" "}
              <Link href={`/cases/${caseId}/ai-analysis`} className="text-brand-700 hover:underline">view</Link>
            </p>
          )}
          <p className="mt-3 rounded bg-slate-100 px-2 py-1.5 text-[11px] text-slate-600">{AI_DISCLAIMER}</p>
        </section>
      </aside>
    </div>
  );
}
