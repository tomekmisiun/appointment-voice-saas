import Link from "next/link";
import { HeroPreview } from "@/components/marketing/HeroPreview";
import { PublicShell } from "@/components/marketing/PublicShell";

const benefits = [
  ["Always available", "Handle calls after hours, during peak times and while your team is with clients."],
  ["Built around your diary", "Book, reschedule and cancel appointments using live availability and staff rules."],
  ["A clearer front desk", "Keep bookings, customer details and call outcomes in one focused workspace."],
];

export default function HomePage() {
  return (
    <PublicShell>
      <section className="public-rings overflow-hidden px-4 pb-16 pt-20 text-center sm:px-6 sm:pt-24">
        <div className="relative z-10 mx-auto max-w-4xl">
          <p className="mb-4 text-sm font-medium text-indigo-300">Automated phone booking for service teams</p>
          <h1 className="text-5xl font-semibold leading-tight text-white sm:text-6xl lg:text-7xl">VoxSlot</h1>
          <p className="mx-auto mt-5 max-w-3xl text-xl leading-8 text-[#9ba7c0] sm:text-2xl">
            A phone receptionist that handles booking calls and keeps your appointment book moving.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Link href="/register" className="rounded-md bg-indigo-500 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-indigo-400">Start free</Link>
            <Link href="/about" className="rounded-md border border-[#303b50] bg-[#182131] px-5 py-3 text-sm font-medium text-[#dde3ef] transition-colors hover:bg-[#202b3d]">See how it works</Link>
          </div>
        </div>
        <HeroPreview />
      </section>

      <section id="how-it-works" className="border-y border-[#1b2434] bg-[#0b111d] px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-6xl">
          <div className="mb-10 max-w-2xl">
            <p className="text-sm font-medium text-indigo-300">One calm workflow</p>
            <h2 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">More answered calls. Less front-desk pressure.</h2>
          </div>
          <div className="grid gap-px overflow-hidden rounded-lg border border-[#253047] bg-[#253047] md:grid-cols-3">
            {benefits.map(([title, description], index) => (
              <article key={title} className="bg-[#111827] p-6 sm:p-8">
                <span className="text-sm font-semibold text-indigo-300">0{index + 1}</span>
                <h3 className="mt-5 text-lg font-semibold text-white">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-[#8d99b1]">{description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>
    </PublicShell>
  );
}
