import Link from "next/link";
import { PublicShell } from "@/components/marketing/PublicShell";

export const metadata = { title: "Resources | VoxSlot" };

const resources = [["Getting started", "Set up your account, business details and first appointment rules.", "/help"], ["Call flow guide", "Understand how VoxSlot moves from a greeting to a confirmed booking.", "/about"], ["Plans and limits", "Compare call volume, calendars and support across each plan.", "/pricing"]] as const;

export default function ResourcesPage() {
  return <PublicShell><section className="public-rings overflow-hidden px-4 py-20 sm:px-6 sm:py-24"><div className="relative z-10 mx-auto max-w-6xl"><p className="text-sm font-medium text-indigo-300">Resources</p><h1 className="mt-3 text-4xl font-semibold text-white sm:text-5xl">Everything you need to get moving</h1><div className="mt-12 grid gap-5 md:grid-cols-3">{resources.map(([title, text, href]) => <Link key={title} href={href} className="rounded-lg border border-[#293449] bg-[#111925] p-7 transition-colors hover:border-indigo-500/70 hover:bg-[#151e2d]"><h2 className="text-lg font-semibold text-white">{title}</h2><p className="mt-3 min-h-16 text-sm leading-6 text-[#8d99b1]">{text}</p><span className="mt-6 block text-sm font-medium text-indigo-300">Open resource →</span></Link>)}</div></div></section></PublicShell>;
}
