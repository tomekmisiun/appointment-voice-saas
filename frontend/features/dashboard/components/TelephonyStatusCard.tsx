"use client";

import { useState } from "react";
import type { BusinessRead } from "@/lib/api/types";

interface TelephonyStatusCardProps {
  business: BusinessRead;
  isDemo?: boolean;
}

export function TelephonyStatusCard({ business, isDemo = false }: TelephonyStatusCardProps) {
  const [copied, setCopied] = useState(false);

  const phone = business.phone ?? null;
  const hasPhone = phone !== null && phone.trim() !== "";

  function handleCopy() {
    if (!phone) return;
    navigator.clipboard.writeText(phone).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">Telephony</h2>
        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
          Active
        </span>
      </div>

      {hasPhone ? (
        <div className="mt-3 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <a
              href={`tel:${phone}`}
              className="font-mono text-base font-semibold text-slate-900 hover:text-indigo-600"
              aria-label={`Call ${phone}`}
            >
              {phone}
            </a>
            <button
              type="button"
              onClick={handleCopy}
              className="rounded border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
              aria-label="Copy phone number"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
          <p className="text-xs text-slate-500">
            Call this number to test the voice booking assistant.
          </p>
          {isDemo ? (
            <p className="text-xs text-amber-700">
              This number belongs to the shared demo environment.
            </p>
          ) : null}
        </div>
      ) : (
        <div className="mt-3">
          <p className="text-xs text-amber-700">
            No phone number configured. Assign a number to enable inbound call routing.
          </p>
        </div>
      )}
    </div>
  );
}
