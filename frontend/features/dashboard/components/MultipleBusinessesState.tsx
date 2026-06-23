import { LogoutButton } from "@/features/auth/components/LogoutButton";
import type { BusinessRead } from "@/lib/api/types";

export function MultipleBusinessesState({ businesses }: { businesses: BusinessRead[] }) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Multiple businesses aren&apos;t supported yet</h2>
        <p className="mt-2 text-sm text-slate-600">
          This account manages more than one active business. The dashboard doesn&apos;t support
          choosing between them yet — this is a known, deliberate limitation, not an error.
        </p>
        <ul className="mt-4 space-y-1 text-sm text-slate-700">
          {businesses.map((business) => (
            <li key={business.id} className="rounded border border-slate-100 bg-slate-50 px-3 py-2">
              {business.name}
            </li>
          ))}
        </ul>
        <div className="mt-4">
          <LogoutButton />
        </div>
      </div>
    </div>
  );
}
