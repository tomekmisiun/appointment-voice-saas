"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { loginRequestSchema, type LoginRequest } from "../schemas";

export function LoginForm() {
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginRequest>({
    resolver: zodResolver(loginRequestSchema),
  });

  async function onSubmit(values: LoginRequest) {
    setServerError(null);

    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });

    if (response.ok) {
      // Hard navigation: the next page is a Server Component that needs
      // the freshly-set session cookie on its own request, not a
      // client-cached router state.
      window.location.assign("/dashboard");
      return;
    }

    const json = await response.json().catch(() => null);
    setServerError(json?.error?.message ?? "Something went wrong. Please try again.");
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-slate-700">
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          aria-invalid={errors.email ? "true" : undefined}
          aria-describedby={errors.email ? "email-error" : undefined}
          className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus-visible:border-blue-500"
          {...register("email")}
        />
        {errors.email ? (
          <p id="email-error" className="mt-1 text-sm text-red-600">
            {errors.email.message}
          </p>
        ) : null}
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium text-slate-700">
          Password
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          aria-invalid={errors.password ? "true" : undefined}
          aria-describedby={errors.password ? "password-error" : undefined}
          className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus-visible:border-blue-500"
          {...register("password")}
        />
        {errors.password ? (
          <p id="password-error" className="mt-1 text-sm text-red-600">
            {errors.password.message}
          </p>
        ) : null}
      </div>

      {serverError ? (
        <p role="alert" className="text-sm text-red-600">
          {serverError}
        </p>
      ) : null}

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? "Signing in…" : "Sign in"}
      </Button>
    </form>
  );
}
