import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../../tests/mocks/server";
import { LoginForm } from "./LoginForm";

describe("LoginForm", () => {
  // jsdom's window.location.assign isn't configurable enough for
  // vi.spyOn directly — replace the whole `location` object for the
  // duration of each test instead.
  const originalLocation = window.location;
  let assignMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    assignMock = vi.fn();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { ...originalLocation, assign: assignMock },
    });
  });

  afterEach(() => {
    Object.defineProperty(window, "location", {
      configurable: true,
      value: originalLocation,
    });
  });

  it("shows validation errors and never calls the network for empty fields", async () => {
    let called = false;
    server.use(
      http.post("/api/auth/login", () => {
        called = true;
        return HttpResponse.json({ ok: true });
      }),
    );
    const user = userEvent.setup();
    render(<LoginForm />);

    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
    expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    expect(called).toBe(false);
  });

  it("shows a validation error for a malformed email without calling the network", async () => {
    let called = false;
    server.use(
      http.post("/api/auth/login", () => {
        called = true;
        return HttpResponse.json({ ok: true });
      }),
    );
    const user = userEvent.setup();
    render(<LoginForm />);

    await user.type(screen.getByLabelText(/email/i), "not-an-email");
    await user.type(screen.getByLabelText(/password/i), "secret123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText(/enter a valid email/i)).toBeInTheDocument();
    expect(called).toBe(false);
  });

  it("navigates to /dashboard on a successful login", async () => {
    server.use(http.post("/api/auth/login", () => HttpResponse.json({ ok: true })));
    const user = userEvent.setup();
    render(<LoginForm />);

    await user.type(screen.getByLabelText(/email/i), "owner@example.com");
    await user.type(screen.getByLabelText(/password/i), "secret123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(assignMock).toHaveBeenCalledWith("/dashboard"));
  });

  it("shows the backend's error message on invalid credentials and does not navigate", async () => {
    server.use(
      http.post("/api/auth/login", () =>
        HttpResponse.json(
          { error: { code: "unauthorized", message: "Invalid email or password" } },
          { status: 401 },
        ),
      ),
    );
    const user = userEvent.setup();
    render(<LoginForm />);

    await user.type(screen.getByLabelText(/email/i), "owner@example.com");
    await user.type(screen.getByLabelText(/password/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");
    expect(assignMock).not.toHaveBeenCalled();
  });
});
