import { redirect } from "next/navigation";
import Link from "next/link";
import { PublicShell } from "@/components/marketing/PublicShell";
import { LoginForm } from "@/features/auth/components/LoginForm";
import { getLoginTenantSlug, getSession, isAccessTokenExpired } from "@/lib/auth/server";

export default async function LoginPage({
  searchParams = Promise.resolve({}),
}: {
  searchParams?: Promise<{ registered?: string }>;
} = {}) {
  const session = await getSession();
  if (session && !isAccessTokenExpired(session)) {
    redirect("/dashboard");
  }
  const [loginTenantSlug, params] = await Promise.all([getLoginTenantSlug(), searchParams]);

  return (
    <PublicShell>
      <section className="public-rings overflow-hidden px-4 py-16 sm:px-6 sm:py-20">
        <div className="relative z-10 mx-auto w-full max-w-sm rounded-lg border border-[#303b50] bg-[#121a28] p-6 shadow-2xl shadow-black/30 sm:p-8">
          <p className="text-sm font-medium text-indigo-300">Welcome back</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">Sign in to VoxSlot</h1>
          <p className="mb-7 mt-2 text-sm text-[#8793aa]">Manage bookings, staff and your phone booking service.</p>
          {params.registered === "1" ? <p className="mb-5 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">Workspace created. Sign in to continue.</p> : null}
          <LoginForm defaultWorkspace={loginTenantSlug} />
          <p className="mt-5 text-center text-sm text-[#7f8ba3]">New to VoxSlot? <Link href="/register" className="text-indigo-300 hover:text-indigo-200">Create an account</Link></p>
        </div>
      </section>
    </PublicShell>
  );
}
