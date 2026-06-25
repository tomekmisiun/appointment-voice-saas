import Link from "next/link";
import { PublicShell } from "@/components/marketing/PublicShell";

export const metadata = { title: "About us | VoxSlot" };

export default function AboutPage() {
  return (
    <PublicShell>
      <section className="public-rings overflow-hidden px-4 pb-24 pt-20 sm:px-6 sm:pt-24">
        <div className="relative z-10 mx-auto max-w-6xl">
          <div className="mx-auto max-w-3xl text-center">
            <p className="text-sm font-medium text-indigo-300">How VoxSlot works</p>
            <h1 className="mt-3 text-4xl font-semibold text-white sm:text-5xl">From phone call to confirmed appointment</h1>
            <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-[#929eb5]">Callers choose a service, preferred staff member and available time by phone. VoxSlot records the booking, updates the calendar and sends confirmation details by SMS.</p>
          </div>

          <div className="relative mx-auto mt-16 min-h-[480px] max-w-4xl" aria-label="A visual overview of the VoxSlot booking workflow">
            <div className="absolute left-[6%] top-10 w-[72%] rounded-lg border border-[#34415a] bg-[#151e2e] p-6 shadow-2xl sm:left-[14%] sm:p-8">
              <div className="flex items-center justify-between border-b border-[#2a354a] pb-5"><span className="font-semibold text-white">Incoming booking call</span><span className="rounded-full bg-emerald-400/15 px-3 py-1 text-xs text-emerald-300">In progress</span></div>
              <div className="grid gap-4 pt-6 sm:grid-cols-3">
                {[["01", "Choose", "Service and preferred staff"], ["02", "Check", "Available dates and times"], ["03", "Confirm", "Booking saved and SMS queued"]].map(([number, title, text]) => <div key={number} className="border-l border-[#34415a] pl-4"><span className="text-xs text-indigo-300">{number}</span><p className="mt-2 text-sm font-medium text-white">{title}</p><p className="mt-1 text-xs leading-5 text-[#8490a8]">{text}</p></div>)}
              </div>
            </div>
            <div className="absolute bottom-7 left-0 w-[48%] rounded-lg border border-[#303b50] bg-[#0e1624] p-5 shadow-xl sm:w-[38%]">
              <p className="text-xs uppercase text-[#6e7b94]">Today</p><p className="mt-2 text-3xl font-semibold text-white">24</p><p className="mt-1 text-sm text-[#8d99b1]">calls handled</p>
            </div>
            <div className="absolute bottom-0 right-0 w-[50%] rounded-lg border border-indigo-500/60 bg-[#171c31] p-5 shadow-xl sm:right-[5%] sm:w-[34%]">
              <p className="text-sm font-medium text-white">Booking confirmed</p><p className="mt-2 text-xs text-[#8d99b1]">Cut & style · Friday, 10:30</p><div className="mt-4 space-y-2 text-xs text-[#a8b2c6]"><p><span className="mr-2 text-emerald-400">✓</span>Confirmation SMS sent</p><p><span className="mr-2 text-indigo-300">✓</span>Calendar event synced</p></div>
            </div>
          </div>

          <div className="mt-12 flex justify-center"><Link href="/register" className="rounded-md bg-indigo-500 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-400">Start business setup</Link></div>
        </div>
      </section>
    </PublicShell>
  );
}
