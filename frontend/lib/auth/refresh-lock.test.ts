import { describe, expect, it } from "vitest";
import { singleFlightRefresh } from "./refresh-lock";

describe("singleFlightRefresh", () => {
  it("runs the operation only once for concurrent calls sharing the same key", async () => {
    let callCount = 0;
    const run = () =>
      new Promise<string>((resolve) => {
        callCount += 1;
        setTimeout(() => resolve("result"), 10);
      });

    const [a, b, c] = await Promise.all([
      singleFlightRefresh("same-token", run),
      singleFlightRefresh("same-token", run),
      singleFlightRefresh("same-token", run),
    ]);

    expect(callCount).toBe(1);
    expect(a).toBe("result");
    expect(b).toBe("result");
    expect(c).toBe("result");
  });

  it("runs the operation again for a different key", async () => {
    let callCount = 0;
    const run = () => {
      callCount += 1;
      return Promise.resolve("result");
    };

    await Promise.all([singleFlightRefresh("token-a", run), singleFlightRefresh("token-b", run)]);

    expect(callCount).toBe(2);
  });

  it("runs the operation again once the previous in-flight call has settled", async () => {
    let callCount = 0;
    const run = () => {
      callCount += 1;
      return Promise.resolve("result");
    };

    await singleFlightRefresh("same-token", run);
    await singleFlightRefresh("same-token", run);

    expect(callCount).toBe(2);
  });

  it("does not cache a rejection — a failed call doesn't poison later calls with the same key", async () => {
    let callCount = 0;
    const run = () => {
      callCount += 1;
      if (callCount === 1) {
        return Promise.reject(new Error("first attempt failed"));
      }
      return Promise.resolve("second attempt result");
    };

    await expect(singleFlightRefresh("same-token", run)).rejects.toThrow("first attempt failed");
    await expect(singleFlightRefresh("same-token", run)).resolves.toBe("second attempt result");
    expect(callCount).toBe(2);
  });
});
