"use client";

import { useState } from "react";
import { useApi } from "@/lib/useApi";
import { humanize, type ComparisonTable, type Institution } from "@/lib/types";
import { Badge, EmptyState, ErrorBox, Loading, PageHeader } from "@/components/ui";

const DEFAULT = ["ICC", "SIAC", "LCIA"];

export default function InstitutionsPage() {
  const { data: institutions, error: instError } = useApi<Institution[]>("/institutions");
  const [selected, setSelected] = useState<string[]>(DEFAULT);
  const { data: table, error, loading } = useApi<ComparisonTable>(
    selected.length ? `/institutions/comparison?institutions=${selected.join(",")}` : null,
  );

  function toggle(name: string) {
    setSelected((prev) => (prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]));
  }

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        title="중재기관"
        subtitle="시딩된 규칙 레코드를 기반으로 절차 단계별 비교표입니다. 각 셀은 해당 조항을 인용하고 공식 출처에 연결됩니다."
      />
      <ErrorBox message={instError ?? error} />

      {institutions && (
        <div className="mb-6 grid gap-4 md:grid-cols-3">
          {institutions.map((i) => (
            <div key={i.id} className="card">
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 font-semibold">
                  <input type="checkbox" checked={selected.includes(i.short_name)} onChange={() => toggle(i.short_name)} className="accent-brand-600" />
                  {i.short_name}
                </label>
                <Badge tone={i.source_tier === "official" ? "green" : "slate"}>{i.source_tier}</Badge>
              </div>
              <p className="mt-1 text-sm text-slate-600">{i.name}</p>
              <p className="mt-2 text-xs text-slate-500">
                규칙 {i.rules_version ?? "—"}{i.rules_effective_date ? ` · 발효일 ${i.rules_effective_date}` : ""}
              </p>
              {i.rules_url && (
                <a href={i.rules_url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-xs text-brand-700 underline">공식 규칙 ↗</a>
              )}
            </div>
          ))}
        </div>
      )}

      {loading && <Loading />}
      {table && table.rows.length === 0 && <EmptyState>선택한 기관에 대한 규칙이 없습니다. 출처를 찾을 수 없습니다.</EmptyState>}
      {table && table.rows.length > 0 && (
        <div className="card overflow-x-auto p-0">
          <table className="table">
            <thead>
              <tr>
                <th className="w-48">단계</th>
                {table.institutions.map((i) => <th key={i.id}>{i.short_name} {i.rules_version}</th>)}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((row) => (
                <tr key={row.stage}>
                  <td className="font-medium text-slate-700">{humanize(row.stage)}</td>
                  {table.institutions.map((i) => {
                    const cells = row.cells[i.short_name] ?? [];
                    return (
                      <td key={i.id}>
                        {cells.length === 0 ? (
                          <span className="text-xs text-slate-400">출처 없음.</span>
                        ) : (
                          <ul className="space-y-1">
                            {cells.map((cell) => (
                              <li key={cell.article_number}>
                                {cell.source_url ? (
                                  <a href={cell.source_url} target="_blank" rel="noreferrer" className="font-medium text-brand-700 underline underline-offset-2">
                                    {cell.article_number}
                                  </a>
                                ) : (
                                  <span className="font-medium">{cell.article_number}</span>
                                )}
                                <span className="text-slate-600"> — {cell.title}</span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-4 text-xs text-slate-500">
        요약문은 탐색 편의를 위해 의역된 것이며 공식 규칙 원문이 아닙니다. 의존하기 전에 반드시 공식 출처에서 각 조항을 확인하세요.
      </p>
    </div>
  );
}
