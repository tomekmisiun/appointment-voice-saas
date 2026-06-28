"use client";

import { useState } from "react";
import type { BusinessRead } from "@/lib/api/types";

interface TelephonyStatusCardProps {
  business: BusinessRead;
  isDemo?: boolean;
}

function maskPhone(phone: string): string {
  if (phone.startsWith("+48") && phone.length === 12) {
    return "+48 *** *** " + phone.slice(-3);
  }
  if (phone.length <= 6) return phone;
  return `${phone.slice(0, -6)}***${phone.slice(-3)}`;
}

function formatVoiceNumber(phone: string): string {
  if (/^\+1\d{10}$/.test(phone)) {
    return `+1 (${phone.slice(2, 5)}) ${phone.slice(5, 8)}-${phone.slice(8)}`;
  }
  return phone;
}

export function TelephonyStatusCard({ business, isDemo = false }: TelephonyStatusCardProps) {
  const [copied, setCopied] = useState(false);

  const servicePhone = business.phone ?? null;
  const hasServicePhone = servicePhone !== null && servicePhone.trim() !== "";
  const displayedServicePhone = hasServicePhone ? formatVoiceNumber(servicePhone!) : null;

  const ownerPhone = business.owner_notification_phone ?? null;
  const hasOwnerPhone = ownerPhone !== null && ownerPhone.trim() !== "";
  const displayedOwnerPhone = hasOwnerPhone && isDemo ? maskPhone(ownerPhone!) : ownerPhone;

  function handleCopy() {
    if (!servicePhone) return;
    navigator.clipboard.writeText(servicePhone).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm space-y-4">
      {/* ── Section 1: Inbound service number ── */}
      <div>
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">Voice number</h2>
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            hasServicePhone ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
          }`}>
            {hasServicePhone ? "Active" : "Not configured"}
          </span>
        </div>

        {hasServicePhone ? (
          <div className="mt-3 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <a
                href={`tel:${servicePhone}`}
                className="font-mono text-base font-semibold text-slate-900 hover:text-indigo-600"
                aria-label={`Call ${servicePhone}`}
              >
                {displayedServicePhone}
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
                This is a US number shared across the demo environment. Calls from Poland
                are billed as international by your carrier.
              </p>
            ) : null}
          </div>
        ) : (
          <div className="mt-3">
            <p className="text-xs text-amber-700">
              No voice number configured. Assign a Twilio number to enable inbound call routing.
            </p>
          </div>
        )}
      </div>

      {/* ── Section 2: Owner notification number ── */}
      <div className="border-t border-slate-100 pt-4">
        <h2 className="text-sm font-semibold text-slate-900">Owner notifications</h2>

        {hasOwnerPhone ? (
          <div className="mt-2 space-y-1">
            <p className="font-mono text-sm text-slate-700">{displayedOwnerPhone}</p>
            <p className="text-xs text-slate-500">
              Booking and cancellation SMS alerts are sent to this number.
            </p>
            {isDemo ? (
              <p className="text-xs text-slate-400">
                Full number visible to the business owner.
              </p>
            ) : null}
          </div>
        ) : (
          <div className="mt-2">
            <p className="text-xs text-amber-700">
              No notification number configured. Set one to receive booking alerts.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
