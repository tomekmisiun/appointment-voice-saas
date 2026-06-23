/** Shared shell for empty/error/blocked-state screens — a centered card with a heading, body, and optional action. */
export function StateMessage({
  title,
  description,
  action,
  tone = "neutral",
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
  tone?: "neutral" | "error";
}) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 text-center shadow-sm">
        <h2 className={`text-lg font-semibold ${tone === "error" ? "text-red-700" : "text-slate-900"}`}>
          {title}
        </h2>
        <p className="mt-2 text-sm text-slate-600">{description}</p>
        {action ? <div className="mt-4">{action}</div> : null}
      </div>
    </div>
  );
}
