import { apiRequest } from "./client";

export type PlayOpeningOption = {
  index: number;
  title: string;
  content: string;
  is_default: boolean;
};

export type PlayCardSummary = {
  id: string;
  name: string;
  description: string | null;
  tags: string[];
  cover_asset_id: string | null;
  avatar_asset_id: string | null;
  latest_session_id: string | null;
  published_at: string | null;
  opening_count: number;
};

export type PlaySessionSummary = {
  id: string;
  name: string;
  status: string;
  card_id: string | null;
  message_count: number;
  last_message_id: string | null;
  last_message_at: string | null;
  current_state_snapshot_id: string | null;
  model_name: string | null;
  created_at: string;
  updated_at: string;
};

export type PlayCardDetail = {
  card: PlayCardSummary;
  openings: PlayOpeningOption[];
  sessions: PlaySessionSummary[];
};

export type SessionResponse = {
  id: string;
  mode: string;
  name: string;
  status: string;
  card_id: string | null;
  card_version_id: string | null;
  worldbook_id: string | null;
  project_id: string | null;
  persona_id: string | null;
  preset_version_id: string | null;
  origin_session_id: string | null;
  origin_snapshot_id: string | null;
  message_count: number;
  last_message_id: string | null;
  last_message_at: string | null;
  current_state_snapshot_id: string | null;
  model_name: string | null;
  created_at: string;
  updated_at: string;
};

export type PlaySessionCreateResponse = {
  session: SessionResponse;
  opening_message_id: string | null;
  opening_selected: PlayOpeningOption | null;
};

export type PlaySessionOverview = {
  session: SessionResponse;
  card: PlayCardSummary;
  openings: PlayOpeningOption[];
  state_summary: string;
};

export type CreatePlaySessionPayload = {
  name: string;
  opening_index?: number;
  model_name?: string;
  use_latest_existing_session?: boolean;
};

export function listPlayCards() {
  return apiRequest<PlayCardSummary[]>("play/cards");
}

export function getPlayCardDetail(cardId: string) {
  return apiRequest<PlayCardDetail>(`play/cards/${cardId}`);
}

export function createPlaySession(cardId: string, payload: CreatePlaySessionPayload) {
  return apiRequest<PlaySessionCreateResponse>(`play/cards/${cardId}/sessions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getPlaySessionOverview(sessionId: string) {
  return apiRequest<PlaySessionOverview>(`play/sessions/${sessionId}/overview`);
}
