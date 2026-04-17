import { apiRequest } from "./client";

export type ConversationSnapshot = {
  id: string;
  session_id: string;
  snapshot_type: string;
  message_id: string | null;
  message_sequence: number;
  inclusive: boolean;
  state_snapshot_id: string | null;
  memory_summary_ids: string[];
  label: string | null;
  summary: Record<string, unknown> | null;
  created_by: string;
  created_at: string;
};

export type RestoreSnapshotResponse = {
  session_id: string;
  snapshot_id: string;
  restored_message_count: number;
  last_message_id: string | null;
  rollback_to_message_id: string | null;
  state_snapshot_id: string | null;
};

export function listSessionSnapshots(sessionId: string) {
  return apiRequest<ConversationSnapshot[]>(`sessions/${sessionId}/snapshots`);
}

export function restoreSnapshot(sessionId: string, snapshotId: string) {
  return apiRequest<RestoreSnapshotResponse>(
    `sessions/${sessionId}/snapshots/${snapshotId}/restore`,
    {
      method: "POST",
    },
  );
}
