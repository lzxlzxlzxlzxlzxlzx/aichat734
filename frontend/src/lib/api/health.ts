import { apiRequest } from "./client";

export type HealthResponse = {
  status: string;
  app_name: string;
  database_path: string;
};

export function getHealth() {
  return apiRequest<HealthResponse>("health");
}
