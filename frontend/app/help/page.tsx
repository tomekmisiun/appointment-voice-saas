import Link from "next/link";
import { PublicShell } from "@/components/marketing/PublicShell";

export const metadata = { title: "Help centre | VoxSlot" };

const categories = ["General topics", "Getting started", "Calls and bookings", "Plans and billing"];
const questions = [
  ["How does VoxSlot answer a customer call?", "VoxSlot follows your services, opening hours, staff availability and booking rules to guide the caller through the right appointment flow."],
  ["Can customers reschedule or cancel?", "Yes. Callers can change an eligible booking while your cancellation windows and business rules remain in effect."],
  ["Can I use my existing business number?", "Number setup depends on your current phone provider. Porting and forwarding guidance will be added to this help centre."],
  ["How are staff calendars kept up to date?", "VoxSlot checks current availability before confirming an appointment, helping avoid overlapping bookings."],
  ["Can I change my plan later?", "Plan changes will be available from billing settings. Contact support while self-service billing is being completed."],
  ["Where can I see call outcomes?", "The owner workspace keeps appointment activity and relevant customer records together for quick review."],
];

export default function HelpPage() {
  return (
    <PublicShell>
      <section className="public-rings overflow-hidden px-4 py-20 sm:px-6 sm:py-24">
        <div className="relative z-10 mx-auto grid max-w-6xl gap-12 lg:grid-cols-[240px_1fr]">
          <aside>
            <div className="rounded-lg border border-[#293449] bg-[#111925] p-3">
              <p className="px-3 pb-3 pt-2 text-sm font-medium text-indigo-300">Help centre</p>
              {categories.map((category, index) => <a key={category} href={`#topic-${index}`} className="block rounded-md px-3 py-2.5 text-sm text-[#8f9bb3] transition-colors hover:bg-[#1b2535] hover:text-white">{category}</a>)}
            </div>
          </aside>
          <div>
            <p className="text-sm font-medium text-indigo-300">Questions and answers</p>
            <h1 className="mt-3 text-4xl font-semibold text-white sm:text-5xl">How can we help?</h1>
            <p className="mt-4 max-w-2xl text-lg text-[#929eb5]">Quick answers for setting up your phone booking line and managing appointments.</p>
            <div className="mt-12 divide-y divide-[#202b3d]">
              {questions.map(([question, answer], index) => (
                <article key={question} id={`topic-${index}`} className="scroll-mt-24 py-6 first:pt-0">
                  <h2 className="text-lg font-semibold text-[#e8ecf4]">{question}</h2>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-[#8d99b1]">{answer}</p>
                </article>
              ))}
            </div>
            <div className="mt-8 border-l-2 border-indigo-500 pl-5">
              <p className="font-medium text-white">Still looking for an answer?</p>
              <p className="mt-1 text-sm text-[#8f9bb3]">More documentation is on the way. For now, <Link href="/register" className="text-indigo-300 hover:text-indigo-200">create an account</Link> to begin setup.</p>
            </div>
          </div>
        </div>
      </section>
    </PublicShell>
  );
}
