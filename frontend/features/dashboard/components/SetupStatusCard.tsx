import type { SetupStatus } from "../setup-status";

export function SetupStatusCard({ status }: { status: SetupStatus }) {
  const items = [status.staff, status.services, status.workingHours];
  const allConfigured = items.every((item) => item.configured);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-900">Setup status</h2>
      <ul className="mt-3 space-y-2">
        {items.map((item) => (
          <li key={item.label} className="flex items-center justify-between text-sm">
            <span className="text-slate-700">{item.label}</span>
            {item.configured ? (
              <span className="text-slate-600">
                {item.countIsFloor ? `${item.count}+` : item.count} configured
              </span>
            ) : (
              <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                Not configured yet
              </span>
            )}
          </li>
        ))}
      </ul>
      {allConfigured ? null : (
        <p className="mt-3 text-xs text-slate-500">
          Staff, services, and working hours all need at least one entry before the IVR can
          offer real booking slots.
        </p>
      )}
    </div>
  );
}
