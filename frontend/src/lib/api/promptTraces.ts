import { apiRequest } from "./client";

export type PromptTraceInspector = {
  id: string;
  session_id: string;
  message_id: string;
  swipe_id: string | null;
  mode: string;
  raw_user_input: string | null;
  normalized_input: string | null;
  injection_count: number;
  final_message_count: number;
  created_at: string;
  final_messages: Array<Record<string, unknown>>;
  injection_items: Array<Record<string, unknown>>;
  request_section: {
    requested_model: string | null;
    provider_name: string | null;
    mode: string | null;
    message_count: number;
    finish_reason: string | null;
  };
  token_section: {
    stats: Record<string, unknown>;
    estimated_input: number | null;
    estimated_output: number | null;
    estimated_total: number | null;
  };
  overview: {
    has_tool_calls: boolean;
    has_regex_hits: boolean;
    has_state_update: boolean;
    tool_call_count: number;
    regex_hit_count: number;
  };
  response_section: {
    cleaned_response: string | null;
    display_response: string | null;
    cleaned_length: number;
    display_length: number;
  };
};

export function getLatestSessionTrace(sessionId: string) {
  return apiRequest<PromptTraceInspector>(`sessions/${sessionId}/traces/latest`);
}

export function getMessageTrace(messageId: string) {
  return apiRequest<PromptTraceInspector>(`messages/${messageId}/trace`);
}
