"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useApi } from "@/lib/useApi";
import type { Case } from "@/lib/types";
import { Badge, ErrorBox } from "@/components/ui";

const TABS = [
  { slug: "overview", label: "개요" },
  { slug: "documents", label: "문서" },
  { slug: "timeline", label: "타임라인" },
  { slug: "claims", label: "청구" },
  { slug: "evidence", label: "증거" },
  { slug: "procedure", label: "절차" },
  { slug: "research", label: "리서치" },
  { slug: "ai-analysis", label: "AI 분석" },
];

export default function CaseLayout({ children }: { children: ReactNode }) {
  const params = useParams<{ caseId: string }>();
  const pathname = usePathname();
  const caseId = params.caseId;
  const { data: c, error } = useApi<Case>(`/cases/${caseId}`);

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-4">
        <Link href="/cases" className="text-xs text-slate-500 hover:text-brand-700">← 전체 사건</Link>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <h1 className="page-title">{c?.title ?? "Case"}</h1>
          {c && <Badge tone="blue">{c.institution}</Badge>}
          {c?.seat && <Badge>중재지: {c.seat}</Badge>}
          {c?.case_ref && <span className="text-xs text-slate-500">{c.case_ref}</span>}
        </div>
      </div>
      <ErrorBox message={error} />
      <nav className="mb-6 flex gap-1 overflow-x-auto border-b border-slate-200" aria-label="Case sections">
        {TABS.map((t) => {
          const href = `/cases/${caseId}/${t.slug}`;
          const active = pathname === href;
          return (
            <Link
              key={t.slug}
              href={href}
              className={`-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm ${active ? "border-brand-600 font-medium text-brand-700" : "border-transparent text-slate-600 hover:text-slate-900"}`}
            >
              {t.label}
            </Link>
          );
        })}
      </nav>
      {children}
    </div>
  );
}
