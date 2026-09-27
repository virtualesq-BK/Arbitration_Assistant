"use client";

import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/useApi";
import { INSTITUTIONS, type AgentResponse, type AgentSource, type Case } from "@/lib/types";
import AIResponseCard from "@/components/AIResponseCard";
import { Badge, ErrorBox, Loading } from "@/components/ui";

interface SearchHit {
  text: string;
  source_name: string;
  source_url: string | null;
  institution: string | null;
  rule_version: string | null;
  document_id: string | null;
  chunk_index: number | null;
  confidence: number;
}

interface SearchResponse {
  results: SearchHit[];
  source_not_found: boolean;
}

const SUGGESTIONS = [
  "What notice requirements apply to extension of time claims under the contract?",
  "When must the Terms of Reference be signed?",
  "What evidence supports the Apron 4 delay?",
  "How is concurrent delay treated?",
];

function SourcePanel({ sources }: { sources: AgentSource[] }) {
  return (
    <aside className="card">
      <h3 className="section-title">Source panel</h3>
      {sources.length === 0 ? (
        <p className="text-sm text-slate-500">Source not found.</p>
      ) : (
        <ol className="space-y-3">
          {sources.map((s) => (
            <li key={s.id} className="rounded-md border border-slate-200 p-3 text-sm">
              <div className="mb-1 flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs text-slate-500">[{s.id}]</span>
                <Badge tone={s.type === "rule" ? "blue" : s.type === "case_document" ? "green" : "slate"}>{s.type.replace("_", " ")}</Badge>
                {s.institution && <Badge tone="blue">{s.institution} {s.rule_version}</Badge>}
              </div>
              <div className="font-medium text-slate-800">{s.source_name ?? s.filename}</div>
              {s.text && <p className="mt-1 line-clamp-4 text-xs text-slate-600">{s.text}</p>}
              {s.source_url && (
                <a href={s.source_url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-xs text-brand-700 underline">
                  Official source ↗
                </a>
              )}
            </li>
          ))}
        </ol>
      )}
    </aside>
  );
}

export default function ResearchPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const { token } = useAuth();
  const { data: c } = useApi<Case>(`/cases/${caseId}`);
  const [query, setQuery] = useState("");
  const [institution, setInstitution] = useState<string>("");
  const [includeCase, setIncludeCase] = useState(true);
  const [response, setResponse] = useState<AgentResponse | null>(null);
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [busy, setBusy] = useState<"ai" | "search" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const inst = institution || c?.institution || "";

  async function runResearch(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!token || query.trim().length < 3) return;
    setBusy("ai");
    setError(null);
    setHits(null);
    try {
      setResponse(
        await apiFetch<AgentResponse>("/research", {
          method: "POST",
          token,
          body: JSON.stringify({ query, institution: inst || null, case_id: includeCase ? caseId : null }),
        }),
      );
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function runSearch() {
    if (!token || !query.trim()) return;
    setBusy("search");
    setError(null);
    setResponse(null);
    try {
      const res = await apiFetch<SearchResponse>("/search", {
        method: "POST",
        token,
        body: JSON.stringify({ query, corpus: "case", case_id: caseId, mode: "hybrid", top_k: 10 }),
      });
      setHits(res.results);
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={runResearch} className="card space-y-3">
        <label htmlFor="q" className="label">Research question</label>
        <textarea id="q" className="input min-h-[80px]" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ask about institutional rules, construction arbitration practice or this case's documents…" />
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button key={s} type="button" className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700 hover:bg-slate-200" onClick={() => setQuery(s)}>{s}</button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label htmlFor="inst" className="text-sm text-slate-600">Rules</label>
            <select id="inst" className="input w-auto" value={institution} onChange={(e) => setInstitution(e.target.value)}>
              <option value="">Case institution ({c?.institution ?? "…"})</option>
              {INSTITUTIONS.map((i) => <option key={i} value={i}>{i}</option>)}
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={includeCase} onChange={(e) => setIncludeCase(e.target.checked)} className="accent-brand-600" />
            Include this case&apos;s documents
          </label>
          <div className="ml-auto flex gap-2">
            <button type="button" className="btn-secondary" onClick={runSearch} disabled={busy !== null}>{busy === "search" ? "Searching…" : "Search documents only"}</button>
            <button type="submit" className="btn-primary" disabled={busy !== null || query.trim().length < 3}>{busy === "ai" ? "Researching…" : "Ask Research Agent"}</button>
          </div>
        </div>
      </form>

      <ErrorBox message={error} />
      {busy && <Loading label={busy === "ai" ? "Retrieving sources and drafting a grounded answer…" : "Searching…"} />}

      {response && (
        <div className="grid gap-6 lg:grid-cols-5">
          <div className="lg:col-span-3"><AIResponseCard response={response} caseId={caseId} /></div>
          <div className="lg:col-span-2"><SourcePanel sources={response.sources} /></div>
        </div>
      )}

      {hits && (
        <section className="card">
          <h3 className="section-title">Document search results ({hits.length})</h3>
          {hits.length === 0 ? (
            <p className="text-sm text-slate-500">Source not found.</p>
          ) : (
            <ol className="space-y-3">
              {hits.map((h, i) => (
                <li key={`${h.document_id}-${h.chunk_index}-${i}`} className="rounded-md border border-slate-200 p-3 text-sm">
                  <div className="mb-1 flex items-center justify-between">
                    <a href={`/cases/${caseId}/documents?doc=${h.document_id}`} className="font-medium text-brand-700 hover:underline">{h.source_name}</a>
                    <span className="text-xs text-slate-400">{Math.round(h.confidence * 100)}% match · chunk {h.chunk_index}</span>
                  </div>
                  <p className="whitespace-pre-line text-xs text-slate-600">{h.text.slice(0, 600)}</p>
                </li>
              ))}
            </ol>
          )}
        </section>
      )}
    </div>
  );
}
