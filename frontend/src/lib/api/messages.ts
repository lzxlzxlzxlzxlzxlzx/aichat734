import { apiRequest } from "./client";

export type MessageSwipe = {
  id: string;
  message_id: string;
  swipe_index: number;
  generation_status: string;
  raw_response: string | null;
  cleaned_response: string | null;
  display_response: string | null;
  provider_name: string | null;
  model_name: string | null;
  finish_reason: string | null;
  token_usage: Record<string, unknown>;
  trace_id: string | null;
  created_at: string;
};

export type MessageAttachment = {
  id: string;
  message_id: string;
  media_asset_id: string;
  attachment_type: string;
  order_index: number;
  caption: string | null;
  created_at: string;
  asset: {
    id: string;
    media_type: string;
    category: string;
    file_name: string;
    file_path: string;
    mime_type: string;
    size_bytes: number;
    meta: Record<string, unknown>;
    created_at: string;
    download_url: string;
  };
};

export type Message = {
  id: string;
  session_id: string;
  role: string;
  sequence: number;
  reply_to_message_id: string | null;
  content: string;
  raw_content: string | null;
  structured_content: Array<Record<string, unknown>> | Array<unknown>;
  active_swipe_id: string | null;
  token_count: number | null;
  is_hidden: boolean;
  is_locked: boolean;
  is_edited: boolean;
  source_type: string;
  created_at: string;
  updated_at: string | null;
  swipes: MessageSwipe[];
  attachments: MessageAttachment[];
};

export type SendMessagePayload = {
  content: string;
  structured_content?: Array<Record<string, unknown>> | Array<unknown>;
  attachments?: Array<unknown>;
  references?: Array<unknown>;
};

export type SendMessageResponse = {
  user_message: Message;
  assistant_message: Message;
};

export type UpdateMessagePayload = {
  content: string;
  structured_content?: Array<Record<string, unknown>> | Array<unknown>;
  attachments?: Array<unknown>;
};

export type UpdateMessageResponse = {
  message: Message;
  truncated_count: number;
};

export type RollbackResponse = {
  session_id: string;
  message_count: number;
  last_message_id: string | null;
  rollback_to_message_id: string | null;
  snapshot_id: string | null;
};

export type DeleteSwipeResponse = {
  message_id: string;
  deleted_swipe_id: string;
  active_swipe_id: string | null;
};

export function listSessionMessages(sessionId: string) {
  return apiRequest<Message[]>(`sessions/${sessionId}/messages`);
}

export function sendSessionMessage(sessionId: string, payload: SendMessagePayload) {
  return apiRequest<SendMessageResponse>(`sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({
      content: payload.content,
      structured_content: payload.structured_content ?? [],
      attachments: payload.attachments ?? [],
      references: payload.references ?? [],
    }),
  });
}

export function updateMessage(messageId: string, payload: UpdateMessagePayload) {
  return apiRequest<UpdateMessageResponse>(`messages/${messageId}`, {
    method: "PATCH",
    body: JSON.stringify({
      content: payload.content,
      structured_content: payload.structured_content ?? [],
      attachments: payload.attachments ?? [],
    }),
  });
}

export function regenerateMessage(messageId: string, modelName?: string) {
  return apiRequest<Message>(`messages/${messageId}/regenerate`, {
    method: "POST",
    body: JSON.stringify({
      model_name: modelName ?? null,
    }),
  });
}

export function activateSwipe(messageId: string, swipeId: string) {
  return apiRequest<Message>(`messages/${messageId}/swipes/${swipeId}/activate`, {
    method: "POST",
  });
}

export function toggleMessageLock(messageId: string, isLocked: boolean) {
  return apiRequest<Message>(`messages/${messageId}/lock`, {
    method: "PATCH",
    body: JSON.stringify({
      is_locked: isLocked,
    }),
  });
}

export function deleteSwipe(messageId: string, swipeId: string) {
  return apiRequest<DeleteSwipeResponse>(`messages/${messageId}/swipes/${swipeId}`, {
    method: "DELETE",
  });
}

export function rollbackFromMessage(sessionId: string, messageId: string) {
  return apiRequest<RollbackResponse>(`sessions/${sessionId}/messages/${messageId}/rollback`, {
    method: "POST",
  });
}
