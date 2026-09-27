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
        title="Arbitration institutions"
        subtitle="Procedure-stage comparison built from seeded rule records. Each cell cites the article and links to the official source."
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
                Rules {i.rules_version ?? "—"}{i.rules_effective_date ? ` · effective ${i.rules_effective_date}` : ""}
              </p>
              {i.rules_url && (
                <a href={i.rules_url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-xs text-brand-700 underline">Official rules ↗</a>
              )}
            </div>
          ))}
        </div>
      )}

      {loading && <Loading />}
      {table && table.rows.length === 0 && <EmptyState>No seeded rules for the selected institutions. Source not found.</EmptyState>}
      {table && table.rows.length > 0 && (
        <div className="card overflow-x-auto p-0">
          <table className="table">
            <thead>
              <tr>
                <th className="w-48">Stage</th>
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
                          <span className="text-xs text-slate-400">Source not found.</span>
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
        Summaries are paraphrased for navigation and are not the official rules text. Verify every provision against the official source before relying on it.
      </p>
    </div>
  );
}
