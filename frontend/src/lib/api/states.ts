import { apiRequest } from "./client";

export type SessionState = {
  session_id: string;
  snapshot_id: string | null;
  state_schema: Record<string, Record<string, unknown>>;
  variables: Record<string, unknown>;
  created_at: string | null;
};

export function getSessionState(sessionId: string) {
  return apiRequest<SessionState>(`sessions/${sessionId}/state`);
}
