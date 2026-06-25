import Link from "next/link";
import { PublicShell } from "@/components/marketing/PublicShell";
import { RegisterForm } from "@/features/auth/components/RegisterForm";

export const metadata = { title: "Create your workspace | VoxSlot" };

export default function RegisterPage() {
  return (
    <PublicShell>
      <section className="public-rings overflow-hidden px-4 py-16 sm:px-6 sm:py-20">
        <div className="relative z-10 mx-auto grid max-w-4xl gap-10 lg:grid-cols-[1fr_390px] lg:items-center">
          <div>
            <p className="text-sm font-medium text-indigo-300">Start with VoxSlot</p>
            <h1 className="mt-3 text-4xl font-semibold text-white sm:text-5xl">Your calls and calendar, working together</h1>
            <p className="mt-5 max-w-lg text-lg leading-8 text-[#929eb5]">Create the owner workspace for your business. You can configure services, staff and booking rules after signing in.</p>
            <ul className="mt-8 space-y-3 text-sm text-[#a4aec1]">
              <li><span className="mr-2 text-indigo-400">✓</span>No payment details required</li>
              <li><span className="mr-2 text-indigo-400">✓</span>Guided business setup</li>
              <li><span className="mr-2 text-indigo-400">✓</span>SMS booking confirmations included</li>
            </ul>
          </div>
          <div className="rounded-lg border border-[#303b50] bg-[#121a28] p-6 shadow-2xl shadow-black/30 sm:p-8">
            <h2 className="text-xl font-semibold text-white">Create an account</h2>
            <p className="mb-6 mt-2 text-sm text-[#8793aa]">Set up your business workspace in a few minutes.</p>
            <RegisterForm />
            <p className="mt-5 text-center text-sm text-[#7f8ba3]">Already registered? <Link href="/login" className="text-indigo-300 hover:text-indigo-200">Sign in</Link></p>
          </div>
        </div>
      </section>
    </PublicShell>
  );
}
