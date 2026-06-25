"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { registerRequestSchema, type RegisterRequest } from "../schemas";

const inputClass = "mt-1 block w-full rounded-md border border-[#344057] bg-[#0d1421] px-3 py-2.5 text-sm text-white placeholder:text-[#5f6b82] focus-visible:border-indigo-400";

export function RegisterForm() {
  const [serverError, setServerError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterRequest>({ resolver: zodResolver(registerRequestSchema) });

  async function onSubmit(values: RegisterRequest) {
    setServerError(null);
    try {
      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      const json = await response.json().catch(() => null);

      if (response.ok) {
        window.location.assign(json?.authenticated === false ? "/login?registered=1" : "/dashboard");
        return;
      }

      setServerError(json?.error?.message ?? "Registration could not be completed. Please try again.");
    } catch {
      setServerError("Registration could not be completed. Please try again.");
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <div>
        <label htmlFor="salon-name" className="block text-sm font-medium text-[#cbd3e2]">Business name</label>
        <input id="salon-name" autoComplete="organization" className={inputClass} aria-invalid={errors.salon_name ? "true" : undefined} aria-describedby={errors.salon_name ? "salon-name-error" : undefined} {...register("salon_name")} />
        {errors.salon_name ? <p id="salon-name-error" className="mt-1 text-sm text-rose-400">{errors.salon_name.message}</p> : null}
      </div>
      <div>
        <label htmlFor="register-email" className="block text-sm font-medium text-[#cbd3e2]">Work email</label>
        <input id="register-email" type="email" autoComplete="email" className={inputClass} aria-invalid={errors.admin_email ? "true" : undefined} aria-describedby={errors.admin_email ? "register-email-error" : undefined} {...register("admin_email")} />
        {errors.admin_email ? <p id="register-email-error" className="mt-1 text-sm text-rose-400">{errors.admin_email.message}</p> : null}
      </div>
      <div>
        <label htmlFor="register-password" className="block text-sm font-medium text-[#cbd3e2]">Password</label>
        <input id="register-password" type="password" autoComplete="new-password" className={inputClass} aria-invalid={errors.admin_password ? "true" : undefined} aria-describedby={errors.admin_password ? "register-password-error" : undefined} {...register("admin_password")} />
        {errors.admin_password ? <p id="register-password-error" className="mt-1 text-sm text-rose-400">{errors.admin_password.message}</p> : <p className="mt-1 text-xs text-[#737f97]">Use at least 8 characters.</p>}
      </div>
      {serverError ? <p role="alert" className="text-sm text-rose-400">{serverError}</p> : null}
      <button type="submit" disabled={isSubmitting} className="inline-flex w-full items-center justify-center rounded-md bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-indigo-800">
        {isSubmitting ? "Creating workspace..." : "Create workspace"}
      </button>
    </form>
  );
}
