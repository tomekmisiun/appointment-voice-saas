import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../../tests/mocks/server";
import { RegisterForm } from "./RegisterForm";

describe("RegisterForm", () => {
  const originalLocation = window.location;
  let assignMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    assignMock = vi.fn();
    Object.defineProperty(window, "location", { configurable: true, value: { ...originalLocation, assign: assignMock } });
  });

  afterEach(() => {
    Object.defineProperty(window, "location", { configurable: true, value: originalLocation });
  });

  it("validates required fields before making a request", async () => {
    const user = userEvent.setup();
    render(<RegisterForm />);

    await user.click(screen.getByRole("button", { name: /create workspace/i }));

    expect(await screen.findByText(/business name is required/i)).toBeInTheDocument();
    expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
  });

  it("redirects to the dashboard after successful registration and automatic login", async () => {
    server.use(http.post("/api/auth/register", () => HttpResponse.json({ ok: true, authenticated: true }, { status: 201 })));
    const user = userEvent.setup();
    render(<RegisterForm />);

    await user.type(screen.getByLabelText(/business name/i), "North Studio");
    await user.type(screen.getByLabelText(/work email/i), "owner@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "secret123");
    await user.click(screen.getByRole("button", { name: /create workspace/i }));

    await waitFor(() => expect(assignMock).toHaveBeenCalledWith("/dashboard"));
  });

  it("redirects to sign in when the workspace was created but automatic login failed", async () => {
    server.use(http.post("/api/auth/register", () => HttpResponse.json({ ok: true, authenticated: false }, { status: 201 })));
    const user = userEvent.setup();
    render(<RegisterForm />);

    await user.type(screen.getByLabelText(/business name/i), "North Studio");
    await user.type(screen.getByLabelText(/work email/i), "owner@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "secret123");
    await user.click(screen.getByRole("button", { name: /create workspace/i }));

    await waitFor(() => expect(assignMock).toHaveBeenCalledWith("/login?registered=1"));
  });

  it("shows a fallback error when the registration request is interrupted", async () => {
    server.use(http.post("/api/auth/register", () => HttpResponse.error()));
    const user = userEvent.setup();
    render(<RegisterForm />);

    await user.type(screen.getByLabelText(/business name/i), "North Studio");
    await user.type(screen.getByLabelText(/work email/i), "owner@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "secret123");
    await user.click(screen.getByRole("button", { name: /create workspace/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not be completed/i);
    expect(assignMock).not.toHaveBeenCalled();
  });

  it("shows a backend registration error", async () => {
    server.use(http.post("/api/auth/register", () => HttpResponse.json({ error: { code: "conflict", message: "Email already exists" } }, { status: 409 })));
    const user = userEvent.setup();
    render(<RegisterForm />);

    await user.type(screen.getByLabelText(/business name/i), "North Studio");
    await user.type(screen.getByLabelText(/work email/i), "owner@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "secret123");
    await user.click(screen.getByRole("button", { name: /create workspace/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Email already exists");
  });
});
