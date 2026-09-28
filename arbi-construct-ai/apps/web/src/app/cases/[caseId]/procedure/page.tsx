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
          <h2 className="section-title mb-0">절차 체크리스트</h2>
          <p className="text-xs text-slate-500">
            각 단계는 {c?.institution ?? "기관"} 규칙 조항에 연결됩니다. AI 제안 단계는 담당 변호사가 반드시 확인해야 합니다. 기한은 중재합의 및 절차명령에 따라 달라집니다.
          </p>
        </div>
        <button type="button" className="btn-secondary" onClick={generate} disabled={busy}>{busy ? "생성 중…" : `${c?.institution ?? ""} 규칙 기반 단계 제안`}</button>
      </div>
      <ErrorBox message={error ?? actionError} />
      {loading && <Loading />}
      {events && events.length === 0 && <EmptyState>아직 절차 단계가 없습니다 — “단계 제안” 버튼으로 규칙 기반 체크리스트를 생성하세요.</EmptyState>}
      {events && events.length > 0 && (
        <div className="card overflow-x-auto p-0">
          <table className="table">
            <thead>
              <tr><th>완료</th><th>단계</th><th>마감</th><th>출처 조항</th><th>상태</th><th>메모</th></tr>
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
                        <Badge tone="purple">AI 제안</Badge>
                        {ev.requires_confirmation && (
                          <button type="button" className="text-xs font-medium text-red-700 underline" onClick={() => update(ev, { requires_confirmation: false })}>
                            ⚠ 단계 확인
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
                      <span className="text-slate-400">출처 없음.</span>
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
