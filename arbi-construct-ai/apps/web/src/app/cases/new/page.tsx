"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { apiFetch, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { INSTITUTIONS, type Case } from "@/lib/types";
import { ErrorBox, PageHeader } from "@/components/ui";

export default function NewCasePage() {
  const { token } = useAuth();
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [institution, setInstitution] = useState<string>("ICC");
  const [seat, setSeat] = useState("");
  const [governingLaw, setGoverningLaw] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const created = await apiFetch<Case>("/cases", {
        method: "POST",
        token,
        body: JSON.stringify({
          title,
          institution,
          seat: seat || null,
          governing_law: governingLaw || null,
          description: description || null,
          amount_in_dispute: amount ? amount : null,
          currency: amount ? currency : null,
        }),
      });
      router.push(`/cases/${created.id}/overview`);
    } catch (err: unknown) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="New case" subtitle="Create an arbitration workspace" />
      <form onSubmit={onSubmit} className="card space-y-4">
        <div>
          <label htmlFor="title" className="label">Title *</label>
          <input id="title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={500} placeholder="e.g. Metro Line 3 Extension Arbitration" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="institution" className="label">Institution *</label>
            <select id="institution" className="input" value={institution} onChange={(e) => setInstitution(e.target.value)}>
              {INSTITUTIONS.map((i) => (
                <option key={i} value={i}>{i}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="seat" className="label">Seat</label>
            <input id="seat" className="input" value={seat} onChange={(e) => setSeat(e.target.value)} placeholder="e.g. Singapore" />
          </div>
        </div>
        <div>
          <label htmlFor="law" className="label">Governing law</label>
          <input id="law" className="input" value={governingLaw} onChange={(e) => setGoverningLaw(e.target.value)} placeholder="e.g. English law" />
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="sm:col-span-2">
            <label htmlFor="amount" className="label">Amount in dispute</label>
            <input id="amount" className="input" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value.replace(/[^0-9.]/g, ""))} />
          </div>
          <div>
            <label htmlFor="currency" className="label">Currency</label>
            <input id="currency" className="input" value={currency} maxLength={3} onChange={(e) => setCurrency(e.target.value.toUpperCase())} />
          </div>
        </div>
        <div>
          <label htmlFor="desc" className="label">Description</label>
          <textarea id="desc" className="input min-h-[96px]" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <ErrorBox message={error} />
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={() => router.back()}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={busy || !title}>{busy ? "Creating…" : "Create case"}</button>
        </div>
      </form>
    </div>
  );
}
