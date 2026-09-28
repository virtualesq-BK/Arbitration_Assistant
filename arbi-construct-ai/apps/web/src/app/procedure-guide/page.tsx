"use client";

import { useEffect, useState } from "react";
import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/useApi";
import { humanize, type Institution, type ProcedureStageResponse } from "@/lib/types";
import AIResponseCard from "@/components/AIResponseCard";
import { EmptyState, ErrorBox, Loading, PageHeader } from "@/components/ui";

export default function ProcedureGuidePage() {
  const { token } = useAuth();
  const { data: institutions, error: instError } = useApi<Institution[]>("/institutions");
  const { data: stages } = useApi<string[]>("/institutions/stages");
  const [institutionId, setInstitutionId] = useState<string>("");
  const [stage, setStage] = useState<string>("NOTICE_OF_ARBITRATION");
  const [withAi, setWithAi] = useState(false);
  const [result, setResult] = useState<ProcedureStageResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!institutionId && institutions && institutions.length > 0) setInstitutionId(institutions[0].id);
  }, [institutions, institutionId]);

  useEffect(() => {
    if (!token || !institutionId || !stage) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiFetch<ProcedureStageResponse>(`/institutions/${institutionId}/procedure/${stage}${withAi ? "?ai=true" : ""}`, { token })
      .then((r) => {
        if (!cancelled) setResult(r);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(errorMessage(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, institutionId, stage, withAi]);

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader title="절차 가이드" subtitle="기관과 절차 단계를 선택하면 해당 규칙 조항과 인용 출처를 확인할 수 있습니다." />
      <ErrorBox message={instError} />

      <div className="card mb-6 grid gap-4 md:grid-cols-3">
        <div>
          <label htmlFor="inst" className="label">1. 중재기관</label>
          <select id="inst" className="input" value={institutionId} onChange={(e) => setInstitutionId(e.target.value)}>
            {(institutions ?? []).map((i) => (
              <option key={i.id} value={i.id}>{i.short_name} — Rules {i.rules_version}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="stage" className="label">2. 절차 단계</label>
          <select id="stage" className="input" value={stage} onChange={(e) => setStage(e.target.value)}>
            {(stages ?? []).map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
          </select>
        </div>
        <div className="flex items-end">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={withAi} onChange={(e) => setWithAi(e.target.checked)} className="accent-brand-600" />
            AI 설명 추가 (절차 에이전트)
          </label>
        </div>
      </div>

      <ErrorBox message={error} />
      {loading && <Loading label={withAi ? "규칙을 불러오고 설명을 생성 중입니다…" : "불러오는 중…"} />}

      {result && !loading && (
        <div className="space-y-6">
          <section className="card">
            <h2 className="section-title">
              {result.institution.short_name} Rules {result.institution.rules_version} — {humanize(result.stage)}
            </h2>
            {result.source_not_found ? (
              <EmptyState>출처를 찾을 수 없습니다. 이 단계에 대한 규칙이 없습니다 — 공식 규칙을 직접 확인하세요.</EmptyState>
            ) : (
              <ul className="space-y-4">
                {result.rules.map((r) => (
                  <li key={r.id} className="rounded-md border border-slate-200 p-4">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <h3 className="font-semibold text-slate-900">{r.article_number} — {r.title}</h3>
                      {r.typical_deadline_days && <span className="text-xs text-slate-500">통상 기간: {r.typical_deadline_days}일</span>}
                    </div>
                    <p className="mt-2 text-sm text-slate-700">{r.summary}</p>
                    {r.notes && <p className="mt-2 text-xs text-slate-500">{r.notes}</p>}
                    <p className="mt-2 text-xs">
                      출처:{" "}
                      {r.source_url ? (
                        <a href={r.source_url} target="_blank" rel="noreferrer" className="text-brand-700 underline">
                          {result.institution.short_name} 규칙 {r.rule_version}, {r.article_number} ↗
                        </a>
                      ) : (
                        "출처 없음."
                      )}
                    </p>
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-4 rounded bg-slate-100 px-3 py-2 text-xs text-slate-600">{result.disclaimer}</p>
          </section>
          {result.ai_guidance && <AIResponseCard response={result.ai_guidance} />}
        </div>
      )}
    </div>
  );
}
