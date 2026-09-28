"use client";

import Link from "next/link";
import { useApi } from "@/lib/useApi";
import { formatMoney, type Case } from "@/lib/types";
import { Badge, EmptyState, ErrorBox, Loading, PageHeader, Stat } from "@/components/ui";

export default function DashboardPage() {
  const { data: cases, error, loading } = useApi<Case[]>("/cases");

  const active = cases?.filter((c) => c.status === "ACTIVE") ?? [];
  const totals = (cases ?? []).reduce(
    (acc, c) => ({
      documents: acc.documents + c.stats.documents,
      claims: acc.claims + c.stats.claims,
      issues: acc.issues + c.stats.issues,
      open: acc.open + c.stats.open_procedural_events,
    }),
    { documents: 0, claims: 0, issues: 0, open: 0 },
  );

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        title="대시보드"
        subtitle="조직의 중재 사건 전체 현황"
        actions={<Link href="/cases/new" className="btn-primary">새 사건</Link>}
      />
      <ErrorBox message={error} />
      {loading && <Loading />}
      {cases && (
        <>
          <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-5">
            <Stat label="진행 중 사건" value={active.length} />
            <Stat label="문서" value={totals.documents} />
            <Stat label="청구" value={totals.claims} />
            <Stat label="기록된 이슈" value={totals.issues} />
            <Stat label="미완료 절차 단계" value={totals.open} />
          </div>

          <h2 className="section-title">사건 목록</h2>
          {cases.length === 0 ? (
            <EmptyState>
              사건이 없습니다. <Link href="/cases/new" className="text-brand-700 underline">첫 사건을 등록하세요</Link>.
            </EmptyState>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {cases.map((c) => (
                <Link key={c.id} href={`/cases/${c.id}/overview`} className="card block transition hover:border-brand-500 hover:shadow">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="font-semibold text-slate-900">{c.title}</h3>
                      <p className="mt-0.5 text-xs text-slate-500">{c.case_ref ?? "참조번호 없음"}</p>
                    </div>
                    <Badge tone={c.status === "ACTIVE" ? "green" : "slate"}>{c.status}</Badge>
                  </div>
                  <dl className="mt-4 grid grid-cols-3 gap-2 text-xs">
                    <div><dt className="text-slate-500">중재기관</dt><dd className="font-medium">{c.institution}</dd></div>
                    <div><dt className="text-slate-500">중재지</dt><dd className="font-medium">{c.seat ?? "—"}</dd></div>
                    <div><dt className="text-slate-500">분쟁금액</dt><dd className="font-medium">{formatMoney(c.amount_in_dispute, c.currency)}</dd></div>
                  </dl>
                  <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-600">
                    <Badge>{c.stats.documents}개 문서</Badge>
                    <Badge>{c.stats.claims}개 청구</Badge>
                    <Badge>{c.stats.timeline_events}개 이벤트</Badge>
                    <Badge tone={c.stats.issues ? "yellow" : "slate"}>{c.stats.issues}개 이슈</Badge>
                    <Badge tone={c.stats.open_procedural_events ? "blue" : "slate"}>{c.stats.open_procedural_events}개 미완료 절차</Badge>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
