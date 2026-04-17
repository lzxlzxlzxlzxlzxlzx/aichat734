import { appConfig } from "../config";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

type RequestOptions = RequestInit & {
  searchParams?: Record<string, string | number | boolean | undefined>;
};

function buildUrl(path: string, searchParams?: RequestOptions["searchParams"]) {
  const url = new URL(path, `${appConfig.apiBaseUrl}/`);

  if (searchParams) {
    Object.entries(searchParams).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    });
  }

  return url.toString();
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { searchParams, headers, body, ...rest } = options;
  const normalizedHeaders = new Headers(headers ?? {});

  if (body && !normalizedHeaders.has("Content-Type")) {
    normalizedHeaders.set("Content-Type", "application/json");
  }

  const response = await fetch(buildUrl(path, searchParams), {
    ...rest,
    headers: normalizedHeaders,
    body,
  });

  if (!response.ok) {
    let errorBody: unknown = null;

    try {
      errorBody = await response.json();
    } catch {
      errorBody = null;
    }

    const message =
      typeof errorBody === "object" &&
      errorBody !== null &&
      "message" in errorBody &&
      typeof errorBody.message === "string"
        ? errorBody.message
        : `Request failed with status ${response.status}`;

    throw new ApiError(message, response.status, errorBody);
  }

  return (await response.json()) as T;
}
