import { PublicShell } from "@/components/marketing/PublicShell";

export const metadata = { title: "Blog | VoxSlot" };

const posts = [
  ["When missed calls become missed revenue", "A practical look at phone demand in appointment-led businesses."],
  ["Designing a calmer booking workflow", "How clear rules help staff, customers and automated assistants work together."],
  ["What customers expect after hours", "Simple ways to keep the path to an appointment open beyond the front desk."],
];

export default function BlogPage() {
  return <PublicShell><section className="public-rings overflow-hidden px-4 py-20 sm:px-6 sm:py-24"><div className="relative z-10 mx-auto max-w-6xl"><p className="text-sm font-medium text-indigo-300">Field notes</p><h1 className="mt-3 text-4xl font-semibold text-white sm:text-5xl">Ideas for a better front desk</h1><div className="mt-12 grid gap-px overflow-hidden rounded-lg border border-[#293449] bg-[#293449] md:grid-cols-3">{posts.map(([title, text], index) => <article key={title} className="bg-[#111925] p-7"><p className="text-xs text-indigo-300">ARTICLE 0{index + 1}</p><h2 className="mt-6 text-xl font-semibold text-white">{title}</h2><p className="mt-3 text-sm leading-6 text-[#8d99b1]">{text}</p><span className="mt-8 block text-sm text-[#65718a]">Coming soon</span></article>)}</div></div></section></PublicShell>;
}
