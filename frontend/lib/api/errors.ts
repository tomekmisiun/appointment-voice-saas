import type { components } from "./schema.gen";

export type ErrorBody = components["schemas"]["ErrorBody"];

/** Thrown by lib/api/server.ts whenever FastAPI responds with a non-2xx status. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly details: ErrorBody["details"] | null;

  constructor(status: number, body: ErrorBody | null) {
    super(body?.message ?? `Backend request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.code = body?.code ?? null;
    this.details = body?.details ?? null;
  }

  get isAuthError(): boolean {
    return this.status === 401;
  }
}

/** Parses the backend's `{error: {code, message, details}}` envelope, if present. */
export async function parseErrorBody(response: Response): Promise<ErrorBody | null> {
  try {
    const json = await response.json();
    if (json && typeof json === "object" && "error" in json) {
      return json.error as ErrorBody;
    }
    return null;
  } catch {
    return null;
  }
}
