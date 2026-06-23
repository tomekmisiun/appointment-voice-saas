import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./mocks/server";

// jsdom doesn't implement HTMLDialogElement.showModal()/close() (still
// "not implemented" as of jsdom 29) — polyfill the open/close behavior
// our native <dialog> confirm UI relies on, just enough for tests. Real
// browsers dispatch a "close" event from close() (components use this to
// sync React state on Escape-key dismissal, which bypasses any onClick
// handler) — dispatch it here too so that behavior is actually exercised
// in tests instead of silently no-op-ing.
if (typeof HTMLDialogElement !== "undefined") {
  HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function (this: HTMLDialogElement) {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
}

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  cleanup();
});
afterAll(() => server.close());
