"use client";

import Link from "next/link";
import { useApi } from "@/lib/useApi";
import { formatMoney, type Case } from "@/lib/types";
import { Badge, EmptyState, ErrorBox, Loading, PageHeader } from "@/components/ui";

export default function CasesPage() {
  const { data: cases, error, loading } = useApi<Case[]>("/cases");

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="Cases" subtitle="All arbitrations in your organisation" actions={<Link href="/cases/new" className="btn-primary">New Case</Link>} />
      <ErrorBox message={error} />
      {loading && <Loading />}
      {cases && cases.length === 0 && <EmptyState>No cases yet.</EmptyState>}
      {cases && cases.length > 0 && (
        <div className="card overflow-x-auto p-0">
          <table className="table">
            <thead>
              <tr>
                <th>Case</th>
                <th>Institution</th>
                <th>Seat</th>
                <th>Governing law</th>
                <th className="text-right">Amount in dispute</th>
                <th>Docs</th>
                <th>Claims</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50">
                  <td>
                    <Link href={`/cases/${c.id}/overview`} className="font-medium text-brand-700 hover:underline">{c.title}</Link>
                    <div className="text-xs text-slate-500">{c.case_ref ?? ""}</div>
                  </td>
                  <td>{c.institution}</td>
                  <td>{c.seat ?? "—"}</td>
                  <td>{c.governing_law ?? "—"}</td>
                  <td className="text-right tabular-nums">{formatMoney(c.amount_in_dispute, c.currency)}</td>
                  <td className="tabular-nums">{c.stats.documents}</td>
                  <td className="tabular-nums">{c.stats.claims}</td>
                  <td><Badge tone={c.status === "ACTIVE" ? "green" : "slate"}>{c.status}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
