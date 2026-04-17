import { apiRequest } from "./client";

export type ChatSessionSummary = {
  id: string;
  name: string;
  status: string;
  message_count: number;
  last_message_id: string | null;
  last_message_at: string | null;
  model_name: string | null;
  created_at: string;
  updated_at: string;
};

export type ChatRecentCard = {
  id: string;
  name: string;
  description: string;
  tags: string[];
  cover_asset_id: string | null;
  avatar_asset_id: string | null;
  latest_session_id: string | null;
  last_interaction_at: string | null;
};

export type ChatQuickReplyItem = {
  id: string;
  label: string;
  content: string;
  mode: string;
  order: number;
};

export type ChatQuickReplyGroup = {
  id: string;
  name: string;
  scope_type: string;
  items: ChatQuickReplyItem[];
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

export type ChatSessionOverview = {
  session: SessionResponse;
  assistant_profile: {
    name: string;
    title: string;
    summary: string;
    traits: string[];
  };
  quick_replies: ChatQuickReplyGroup[];
  recent_cards: ChatRecentCard[];
  latest_trace: {
    id: string;
    session_id: string;
    message_id: string;
    swipe_id: string | null;
    mode: string;
    created_at: string;
  } | null;
};

export function listChatSessions() {
  return apiRequest<ChatSessionSummary[]>("chat/sessions");
}

export function createChatSession(payload: { name?: string | null; model_name?: string | null } = {}) {
  return apiRequest<SessionResponse>("chat/sessions", {
    method: "POST",
    body: JSON.stringify({
      name: payload.name ?? null,
      model_name: payload.model_name ?? null,
    }),
  });
}

export function getChatSessionOverview(sessionId: string) {
  return apiRequest<ChatSessionOverview>(`chat/sessions/${sessionId}/overview`);
}

export function renameChatSession(sessionId: string, name: string) {
  return apiRequest<SessionResponse>(`chat/sessions/${sessionId}/rename`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export function updateChatSessionModel(sessionId: string, modelName: string) {
  return apiRequest<SessionResponse>(`chat/sessions/${sessionId}/model`, {
    method: "PATCH",
    body: JSON.stringify({ model_name: modelName }),
  });
}

export function deleteChatSession(sessionId: string) {
  return apiRequest<SessionResponse>(`chat/sessions/${sessionId}`, {
    method: "DELETE",
  });
}

export function listRecentCards(limit = 8) {
  return apiRequest<ChatRecentCard[]>("chat/recent-cards", {
    searchParams: { limit },
  });
}

export function listChatQuickReplies(sessionId: string) {
  return apiRequest<ChatQuickReplyGroup[]>(`chat/sessions/${sessionId}/quick-replies`);
}
