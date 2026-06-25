"use client";

import Link from "next/link";
import { useState } from "react";

const plans = [
  { name: "Starter", description: "For solo appointment professionals.", features: ["Phone call handling", "Booking request capture", "SMS follow-up", "Basic calendar setup"] },
  { name: "Studio", description: "For small teams with a busy diary.", features: ["Team call flows", "Staff-aware booking", "Customer records", "Operational summaries"] },
  { name: "Business", description: "For growing multi-staff businesses.", features: ["Advanced booking rules", "Waitlist workflows", "Calendar coordination", "Priority onboarding"], popular: true },
  { name: "Enterprise", description: "For high-volume or multi-location teams.", features: ["Multi-location setup", "Custom integrations", "Dedicated onboarding", "Operational support"] },
];

export function PricingTable() {
  const [annual, setAnnual] = useState(true);

  return (
    <>
      <div className="mt-8 flex items-center justify-center gap-3 text-sm text-[#8f9bb3]">
        <span className={annual ? "text-white" : undefined}>Billed annually</span>
        <button
          type="button"
          role="switch"
          aria-checked={!annual}
          aria-label="Switch between annual and monthly billing"
          className="relative h-7 w-12 rounded-full bg-indigo-500 p-1"
          onClick={() => setAnnual((value) => !value)}
        >
          <span className={`block h-5 w-5 rounded-full bg-white transition-transform ${annual ? "" : "translate-x-5"}`} />
        </button>
        <span className={!annual ? "text-white" : undefined}>Billed monthly</span>
      </div>

      <div className="mt-14 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {plans.map((plan) => {
          return (
            <article key={plan.name} className={`relative flex min-h-[420px] flex-col rounded-lg border p-5 ${plan.popular ? "border-indigo-500 bg-[#151b2c] shadow-xl shadow-indigo-950/30" : "border-[#293449] bg-[#111925]"}`}>
              {plan.popular ? <span className="absolute right-4 top-4 rounded-full bg-indigo-500/20 px-2.5 py-1 text-xs font-medium text-indigo-300">Popular</span> : null}
              <h2 className="text-base font-medium text-[#e1e6ef]">{plan.name}</h2>
              <p className="mt-5 text-3xl font-semibold text-white">Coming soon</p>
              <p className="mt-2 min-h-10 text-sm leading-5 text-[#8793aa]">{plan.description}</p>
              <Link href="/register" className={`mt-5 rounded-md px-4 py-2.5 text-center text-sm font-medium transition-colors ${plan.popular ? "bg-indigo-500 text-white hover:bg-indigo-400" : "border border-[#303b50] bg-[#1d2736] text-[#e2e7f0] hover:bg-[#273347]"}`}>Join early access</Link>
              <div className="my-6 h-px bg-[#283247]" />
              <p className="mb-4 text-sm font-medium text-[#dce2ed]">What&apos;s included</p>
              <ul className="space-y-3">
                {plan.features.map((feature) => <li key={feature} className="flex gap-2 text-sm text-[#8f9bb3]"><span className="text-indigo-400" aria-hidden="true">✓</span>{feature}</li>)}
              </ul>
            </article>
          );
        })}
      </div>
      <p className="mt-6 text-center text-sm text-[#7e8aa2]">Plan packaging is not active yet. Early workspaces can register without choosing a paid plan.</p>
    </>
  );
}
