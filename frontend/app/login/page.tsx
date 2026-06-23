import { redirect } from "next/navigation";
import { LoginForm } from "@/features/auth/components/LoginForm";
import { getSession, isAccessTokenExpired } from "@/lib/auth/server";

export default async function LoginPage() {
  const session = await getSession();
  if (session && !isAccessTokenExpired(session)) {
    redirect("/dashboard");
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-6 text-center text-xl font-semibold text-slate-900">Sign in</h1>
        <LoginForm />
      </div>
    </main>
  );
}
