const DEFAULT_API_BASE_URL = "http://127.0.0.1:7734/v1";

export const appConfig = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL,
};
