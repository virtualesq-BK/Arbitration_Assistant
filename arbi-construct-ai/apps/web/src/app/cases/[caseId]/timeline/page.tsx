"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/useApi";
import { humanize, type DocumentItem, type TimelineEvent } from "@/lib/types";
import { Badge, EmptyState, ErrorBox, Loading, type Tone } from "@/components/ui";

const TYPE_TONES: Record<string, Tone> = {
  DELAY_EVENT: "red",
  NOTICE: "yellow",
  CLAIM: "purple",
  ARBITRATION: "blue",
  PAYMENT: "green",
};

export default function TimelinePage() {
  const { caseId } = useParams<{ caseId: string }>();
  const { token } = useAuth();
  const { data: events, error, loading, reload } = useApi<TimelineEvent[]>(`/cases/${caseId}/timeline`);
  const { data: docs } = useApi<DocumentItem[]>(`/cases/${caseId}/documents`);

  const [date, setDate] = useState("");
  const [description, setDescription] = useState("");
  const [eventType, setEventType] = useState("GENERAL");
  const [docId, setDocId] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setFormError(null);
    try {
      await apiFetch<TimelineEvent>(`/cases/${caseId}/timeline`, {
        method: "POST",
        token,
        body: JSON.stringify({ event_date: date, description, event_type: eventType, source_document_id: docId || null }),
      });
      setDate("");
      setDescription("");
      setDocId("");
      reload();
    } catch (err: unknown) {
      setFormError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <section className="lg:col-span-2">
        <h2 className="section-title">연표</h2>
        <ErrorBox message={error} />
        {loading && <Loading />}
        {events && events.length === 0 && <EmptyState>타임라인 이벤트가 없습니다.</EmptyState>}
        {events && events.length > 0 && (
          <ol className="relative ml-3 border-l-2 border-slate-200">
            {events.map((ev) => (
              <li key={ev.id} className="mb-6 ml-6">
                <span className="absolute -left-[9px] mt-1.5 h-4 w-4 rounded-full border-2 border-white bg-brand-500 ring-2 ring-brand-100" aria-hidden="true" />
                <div className="flex flex-wrap items-center gap-2">
                  <time className="font-mono text-sm font-semibold text-slate-900">{ev.event_date}</time>
                  <Badge tone={TYPE_TONES[ev.event_type] ?? "slate"}>{humanize(ev.event_type)}</Badge>
                  {ev.is_ai_extracted && <Badge tone="purple">AI 추출</Badge>}
                </div>
                <p className="mt-1 text-sm text-slate-800">{ev.description}</p>
                {ev.source_document_id && (
                  <p className="mt-1 text-xs text-slate-500">
                    Source:{" "}
                    <Link href={`/cases/${caseId}/documents?doc=${ev.source_document_id}`} className="text-brand-700 underline underline-offset-2">
                      {ev.source_document_filename ?? "document"}
                    </Link>
                    {ev.source_page ? `, ${ev.source_page}페이지` : ""}
                  </p>
                )}
              </li>
            ))}
          </ol>
        )}
      </section>

      <aside>
        <form onSubmit={onSubmit} className="card space-y-3">
          <h2 className="section-title">이벤트 추가</h2>
          <div>
            <label htmlFor="edate" className="label">날짜 *</label>
            <input id="edate" type="date" className="input" value={date} onChange={(e) => setDate(e.target.value)} required />
          </div>
          <div>
            <label htmlFor="etype" className="label">유형</label>
            <select id="etype" className="input" value={eventType} onChange={(e) => setEventType(e.target.value)}>
              {["GENERAL", "DELAY_EVENT", "NOTICE", "INSTRUCTION", "VARIATION", "PAYMENT", "CLAIM", "SITE_RECORD", "ARBITRATION"].map((t) => (
                <option key={t} value={t}>{humanize(t)}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="edesc" className="label">설명 *</label>
            <textarea id="edesc" className="input min-h-[80px]" value={description} onChange={(e) => setDescription(e.target.value)} required />
          </div>
          <div>
            <label htmlFor="edoc" className="label">출처 문서</label>
            <select id="edoc" className="input" value={docId} onChange={(e) => setDocId(e.target.value)}>
              <option value="">— 없음 —</option>
              {(docs ?? []).map((d) => <option key={d.id} value={d.id}>{d.filename}</option>)}
            </select>
          </div>
          <ErrorBox message={formError} />
          <button type="submit" className="btn-primary w-full" disabled={busy}>{busy ? "저장 중…" : "타임라인에 추가"}</button>
        </form>
      </aside>
    </div>
  );
}
