"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "@/lib/auth";

const NAV = [
  { href: "/dashboard", label: "대시보드" },
  { href: "/cases", label: "사건" },
  { href: "/arbitration-institutions", label: "중재기관" },
  { href: "/procedure-guide", label: "절차 가이드" },
];

export const LEGAL_DISCLAIMER =
  "ArbiConstruct AI는 AI 기반 정보 관리 및 리서치 서비스를 제공합니다. 법률 자문 또는 법률 대리인 서비스가 아닙니다. AI 결과물은 반드시 자격을 갖춘 법률 전문가의 검토를 거쳐야 합니다.";

const PUBLIC_PATHS = ["/login", "/"];

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { token, ready, logout } = useAuth();
  const isPublic = PUBLIC_PATHS.includes(pathname);

  useEffect(() => {
    if (ready && !token && !isPublic) router.replace("/login");
  }, [ready, token, isPublic, router]);

  const footer = (
    <footer className="border-t border-slate-200 bg-white px-6 py-3 text-xs text-slate-500">{LEGAL_DISCLAIMER}</footer>
  );

  if (isPublic) {
    return (
      <div className="flex min-h-screen flex-col">
        <main className="flex-1">{children}</main>
        {footer}
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="flex shrink-0 flex-col bg-brand-900 text-slate-200 md:w-60">
        <div className="px-5 py-5">
          <Link href="/dashboard" className="block text-lg font-semibold text-white">
            ArbiConstruct <span className="text-brand-100">AI</span>
          </Link>
          <p className="mt-0.5 text-[11px] uppercase tracking-wider text-slate-400">건설 중재</p>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:overflow-visible">
          {NAV.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`whitespace-nowrap rounded-md px-3 py-2 text-sm ${active ? "bg-white/10 font-medium text-white" : "text-slate-300 hover:bg-white/5 hover:text-white"}`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto hidden px-5 py-4 md:block">
          <button
            type="button"
            onClick={() => {
              logout();
              router.replace("/login");
            }}
            className="text-xs text-slate-400 hover:text-white"
          >
            로그아웃
          </button>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <main className="flex-1 px-4 py-6 md:px-8">{ready && token ? children : null}</main>
        {footer}
      </div>
    </div>
  );
}
