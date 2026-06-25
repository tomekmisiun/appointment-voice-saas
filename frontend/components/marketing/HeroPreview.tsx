const bookings = [
  { time: "09:00", name: "Maya Wilson", service: "Cut & style", tone: "bg-indigo-500" },
  { time: "10:30", name: "Noah Brown", service: "Beard trim", tone: "bg-cyan-500" },
  { time: "12:00", name: "Olivia Smith", service: "Colour session", tone: "bg-fuchsia-500" },
];

export function HeroPreview() {
  return (
    <div className="relative mx-auto mt-12 w-full max-w-5xl overflow-hidden rounded-lg border border-[#29344a] bg-[#111827] shadow-2xl shadow-indigo-950/40" aria-label="VoxSlot appointment dashboard preview">
      <div className="flex h-11 items-center justify-between border-b border-[#253047] px-4">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-rose-400" />
          <span className="h-2 w-2 rounded-full bg-amber-400" />
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
        </div>
        <span className="text-xs text-[#77839d]">Today, 14 March</span>
      </div>
      <div className="grid min-h-[330px] grid-cols-1 md:grid-cols-[180px_1fr]">
        <aside className="hidden border-r border-[#253047] bg-[#0d1421] p-4 md:block">
          <p className="mb-5 text-xs font-semibold uppercase text-[#66728a]">Workspace</p>
          {['Overview', 'Bookings', 'Staff', 'Clients'].map((item, index) => (
            <div key={item} className={`mb-1 rounded-md px-3 py-2 text-sm ${index === 1 ? 'bg-indigo-500/15 text-indigo-300' : 'text-[#8793aa]'}`}>{item}</div>
          ))}
        </aside>
        <div className="p-5 sm:p-7">
          <div className="mb-6 flex items-end justify-between">
            <div>
              <p className="text-xs uppercase text-[#76829a]">Good morning</p>
              <h2 className="mt-1 text-xl font-semibold">Today&apos;s appointments</h2>
            </div>
            <span className="rounded-md bg-indigo-500 px-3 py-2 text-xs font-medium text-white">+ New booking</span>
          </div>
          <div className="grid gap-3">
            {bookings.map((booking) => (
              <div key={booking.time} className="grid grid-cols-[52px_1fr_auto] items-center gap-3 rounded-lg border border-[#263149] bg-[#151e2e] p-3 sm:p-4">
                <p className="text-sm font-semibold text-white">{booking.time}</p>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-[#e8ecf4]">{booking.name}</p>
                  <p className="truncate text-xs text-[#7e8aa3]">{booking.service}</p>
                </div>
                <span className={`h-2.5 w-2.5 rounded-full ${booking.tone}`} title="Confirmed" />
              </div>
            ))}
          </div>
          <div className="mt-4 flex items-center gap-2 text-xs text-[#8793aa]">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Phone booking line online and taking calls
          </div>
        </div>
      </div>
    </div>
  );
}
