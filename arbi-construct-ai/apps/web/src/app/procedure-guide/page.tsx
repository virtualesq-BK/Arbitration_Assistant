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
      <PageHeader title="Procedure guide" subtitle="Select an institution and a procedural stage to see the applicable rule provisions with citations." />
      <ErrorBox message={instError} />

      <div className="card mb-6 grid gap-4 md:grid-cols-3">
        <div>
          <label htmlFor="inst" className="label">1. Institution</label>
          <select id="inst" className="input" value={institutionId} onChange={(e) => setInstitutionId(e.target.value)}>
            {(institutions ?? []).map((i) => (
              <option key={i.id} value={i.id}>{i.short_name} — Rules {i.rules_version}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="stage" className="label">2. Stage</label>
          <select id="stage" className="input" value={stage} onChange={(e) => setStage(e.target.value)}>
            {(stages ?? []).map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
          </select>
        </div>
        <div className="flex items-end">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={withAi} onChange={(e) => setWithAi(e.target.checked)} className="accent-brand-600" />
            Add AI explanation (Procedure Agent)
          </label>
        </div>
      </div>

      <ErrorBox message={error} />
      {loading && <Loading label={withAi ? "Loading rules and generating explanation…" : "Loading…"} />}

      {result && !loading && (
        <div className="space-y-6">
          <section className="card">
            <h2 className="section-title">
              {result.institution.short_name} Rules {result.institution.rules_version} — {humanize(result.stage)}
            </h2>
            {result.source_not_found ? (
              <EmptyState>Source not found. No seeded provision for this stage — consult the official rules.</EmptyState>
            ) : (
              <ul className="space-y-4">
                {result.rules.map((r) => (
                  <li key={r.id} className="rounded-md border border-slate-200 p-4">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <h3 className="font-semibold text-slate-900">{r.article_number} — {r.title}</h3>
                      {r.typical_deadline_days && <span className="text-xs text-slate-500">Typical period: {r.typical_deadline_days} days</span>}
                    </div>
                    <p className="mt-2 text-sm text-slate-700">{r.summary}</p>
                    {r.notes && <p className="mt-2 text-xs text-slate-500">{r.notes}</p>}
                    <p className="mt-2 text-xs">
                      Source:{" "}
                      {r.source_url ? (
                        <a href={r.source_url} target="_blank" rel="noreferrer" className="text-brand-700 underline">
                          {result.institution.short_name} Rules {r.rule_version}, {r.article_number} ↗
                        </a>
                      ) : (
                        "Source not found."
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
