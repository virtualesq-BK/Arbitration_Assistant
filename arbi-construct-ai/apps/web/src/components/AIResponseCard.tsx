import type { AgentResponse, AgentSource, FindingLabel } from "@/lib/types";

export const AI_DISCLAIMER =
  "AI-assisted analysis. Final legal judgment must be performed by qualified legal professionals.";

const LABEL_STYLES: Record<FindingLabel, string> = {
  FACT: "bg-emerald-100 text-emerald-800 ring-emerald-300",
  SOURCE_BASED_INFO: "bg-blue-100 text-blue-800 ring-blue-300",
  AI_SUMMARY: "bg-violet-100 text-violet-800 ring-violet-300",
  POTENTIAL_ISSUE: "bg-orange-100 text-orange-800 ring-orange-300",
  POTENTIAL_EVIDENCE_GAP: "bg-amber-100 text-amber-900 ring-amber-300",
  REQUIRES_HUMAN_REVIEW: "bg-red-100 text-red-800 ring-red-300",
};

export function FindingBadge({ label }: { label: FindingLabel }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset ${LABEL_STYLES[label] ?? LABEL_STYLES.AI_SUMMARY}`}
    >
      {label === "REQUIRES_HUMAN_REVIEW" && <span aria-hidden="true" className="mr-1">⚠</span>}
      {label.replace(/_/g, " ")}
    </span>
  );
}

function sourceTitle(s: AgentSource): string {
  if (s.type === "case_document") {
    return `${s.filename ?? s.source_name ?? "Case document"}${s.chunk_index !== null && s.chunk_index !== undefined ? ` · chunk ${s.chunk_index}` : ""}`;
  }
  if (s.type === "rule") {
    return [s.institution, s.rule_version, s.source_name].filter(Boolean).join(" · ");
  }
  return s.source_name ?? s.filename ?? s.type;
}

function sourceHref(s: AgentSource, caseId?: string): string | null {
  if (s.source_url) return s.source_url;
  if (s.type === "case_document" && s.document_id && caseId) return `/cases/${caseId}/documents?doc=${s.document_id}`;
  return null;
}

export default function AIResponseCard({ response, caseId }: { response: AgentResponse; caseId?: string }) {
  const sourceIds = new Set(response.sources.map((s) => s.id));
  return (
    <article className="card space-y-5" aria-label={`${response.agent} output`}>
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="rounded bg-slate-900 px-2 py-0.5 text-xs font-semibold text-white">{response.agent}</span>
          <span className="text-xs text-slate-500">model: {response.model}</span>
        </div>
        {response.analysis_id && <span className="font-mono text-[11px] text-slate-400">audit #{response.analysis_id.slice(0, 8)}</span>}
      </header>

      <section>
        <div className="mb-1 flex items-center gap-2">
          <FindingBadge label="AI_SUMMARY" />
          <h3 className="text-sm font-semibold text-slate-700">Summary</h3>
        </div>
        <p className="whitespace-pre-line text-sm leading-relaxed text-slate-800">{response.summary}</p>
      </section>

      {response.requires_human_review.length > 0 && (
        <section className="rounded-md border border-red-300 bg-red-50 p-4">
          <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-red-800">
            <span aria-hidden="true">⚠</span> Requires human review ({response.requires_human_review.length})
          </h3>
          <ul className="space-y-1.5 text-sm text-red-900">
            {response.requires_human_review.map((item, i) => (
              <li key={i} className="flex gap-2">
                <span aria-hidden="true">⚠</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {response.evidence_gaps.length > 0 && (
        <section className="rounded-md border border-amber-300 bg-amber-50 p-4">
          <h3 className="mb-2 text-sm font-semibold text-amber-900">Potential evidence gaps ({response.evidence_gaps.length})</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-amber-900">
            {response.evidence_gaps.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </section>
      )}

      {response.findings.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-semibold text-slate-700">Findings ({response.findings.length})</h3>
          <ul className="divide-y divide-slate-100 rounded-md border border-slate-200">
            {response.findings.map((f, i) => (
              <li
                key={i}
                className={`flex flex-col gap-2 p-3 sm:flex-row sm:items-start ${f.label === "REQUIRES_HUMAN_REVIEW" ? "bg-red-50/60" : f.label === "POTENTIAL_EVIDENCE_GAP" ? "bg-amber-50/60" : ""}`}
              >
                <FindingBadge label={f.label} />
                <div className="min-w-0 flex-1 text-sm text-slate-800">
                  <p className="whitespace-pre-line break-words">{f.content}</p>
                  {f.citations.length > 0 && (
                    <p className="mt-1 flex flex-wrap gap-1">
                      {f.citations.map((c) => (
                        <a
                          key={c}
                          href={sourceIds.has(c) ? `#src-${response.analysis_id ?? "x"}-${c}` : undefined}
                          className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-brand-700 hover:bg-brand-50"
                        >
                          [{c}]
                        </a>
                      ))}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Sources ({response.sources.length})</h3>
        {response.sources.length === 0 ? (
          <p className="text-sm text-slate-500">Source not found.</p>
        ) : (
          <ol className="space-y-1.5 text-sm">
            {response.sources.map((s) => {
              const href = sourceHref(s, caseId);
              return (
                <li key={s.id} id={`src-${response.analysis_id ?? "x"}-${s.id}`} className="flex gap-2">
                  <span className="font-mono text-xs text-slate-500">[{s.id}]</span>
                  {href ? (
                    <a
                      href={href}
                      target={href.startsWith("http") ? "_blank" : undefined}
                      rel="noreferrer"
                      className="text-brand-700 underline decoration-brand-100 underline-offset-2 hover:decoration-brand-500"
                    >
                      {sourceTitle(s)}
                    </a>
                  ) : (
                    <span className="text-slate-700">{sourceTitle(s)}</span>
                  )}
                  {typeof s.confidence === "number" && s.type !== "case_record" && (
                    <span className="text-xs text-slate-400">({Math.round(s.confidence * 100)}% match)</span>
                  )}
                </li>
              );
            })}
          </ol>
        )}
      </section>

      <footer className="rounded-md bg-slate-100 px-3 py-2 text-xs font-medium text-slate-600">
        {response.disclaimer || AI_DISCLAIMER}
      </footer>
    </article>
  );
}
