import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bot,
  ChevronDown,
  Copy,
  MessageCircleMore,
  PanelRightOpen,
  Pencil,
  Plus,
  RotateCcw,
  Save,
  SendHorizonal,
  Sparkles,
  Trash2,
} from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { StatusCard } from "../../../components/common/StatusCard";
import {
  createChatSession,
  deleteChatSession,
  getChatSessionOverview,
  listChatQuickReplies,
  listChatSessions,
  renameChatSession,
  updateChatSessionModel,
  type ChatQuickReplyGroup,
  type ChatSessionSummary,
} from "../../../lib/api/chat";
import {
  listSessionMessages,
  rollbackFromMessage,
  sendSessionMessage,
  type Message,
} from "../../../lib/api/messages";
import {
  getLatestSessionTrace,
  getMessageTrace,
  type PromptTraceInspector,
} from "../../../lib/api/promptTraces";
import { formatDateTime, formatRelativeTime } from "../../../lib/format";

export function ChatPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameDraft, setRenameDraft] = useState("");
  const [selectedPromptMessageId, setSelectedPromptMessageId] = useState<string | null>(null);

  const sessionsQuery = useQuery({
    queryKey: ["chat", "sessions"],
    queryFn: listChatSessions,
  });
  const overviewQuery = useQuery({
    queryKey: ["chat", "session-overview", sessionId],
    queryFn: () => getChatSessionOverview(sessionId!),
    enabled: Boolean(sessionId),
  });
  const quickRepliesQuery = useQuery({
    queryKey: ["chat", "quick-replies", sessionId],
    queryFn: () => listChatQuickReplies(sessionId!),
    enabled: Boolean(sessionId),
  });
  const messagesQuery = useQuery({
    queryKey: ["chat", "messages", sessionId],
    queryFn: () => listSessionMessages(sessionId!),
    enabled: Boolean(sessionId),
  });
  const traceQuery = useQuery({
    queryKey: ["chat", "trace-latest", sessionId],
    queryFn: () => getLatestSessionTrace(sessionId!),
    enabled: Boolean(sessionId),
  });
  const promptQuery = useQuery({
    queryKey: ["chat", "message-trace", selectedPromptMessageId],
    queryFn: () => getMessageTrace(selectedPromptMessageId!),
    enabled: Boolean(selectedPromptMessageId),
    retry: false,
  });

  async function refreshChatQueries() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["chat", "sessions"] }),
      queryClient.invalidateQueries({ queryKey: ["chat", "session-overview", sessionId] }),
      queryClient.invalidateQueries({ queryKey: ["chat", "quick-replies", sessionId] }),
      queryClient.invalidateQueries({ queryKey: ["chat", "messages", sessionId] }),
      queryClient.invalidateQueries({ queryKey: ["chat", "trace-latest", sessionId] }),
    ]);
  }

  const createSessionMutation = useMutation({
    mutationFn: () => createChatSession({}),
    onSuccess: async (session) => {
      await queryClient.invalidateQueries({ queryKey: ["chat", "sessions"] });
      navigate(`/chat/${session.id}`);
    },
  });

  const deleteSessionMutation = useMutation({
    mutationFn: (targetSessionId: string) => deleteChatSession(targetSessionId),
    onSuccess: async (_, deletedSessionId) => {
      await queryClient.invalidateQueries({ queryKey: ["chat", "sessions"] });
      if (deletedSessionId === sessionId) {
        navigate("/chat");
      }
    },
  });

  const sendMutation = useMutation({
    mutationFn: (content: string) => sendSessionMessage(sessionId!, { content }),
    onSuccess: async () => {
      setDraft("");
      await refreshChatQueries();
    },
  });

  const renameMutation = useMutation({
    mutationFn: (name: string) => renameChatSession(sessionId!, name),
    onSuccess: async () => {
      setIsRenaming(false);
      await refreshChatQueries();
    },
  });

  const updateModelMutation = useMutation({
    mutationFn: (modelName: string) => updateChatSessionModel(sessionId!, modelName),
    onSuccess: refreshChatQueries,
  });

  const rollbackMutation = useMutation({
    mutationFn: (messageId: string) => rollbackFromMessage(sessionId!, messageId),
    onSuccess: refreshChatQueries,
  });

  const messages = messagesQuery.data ?? [];
  const quickReplyGroups = quickRepliesQuery.data ?? [];
  const overview = overviewQuery.data;
  const latestTrace = traceQuery.data;
  const sessions = sessionsQuery.data ?? [];

  function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || sendMutation.isPending || !sessionId) {
      return;
    }
    sendMutation.mutate(content);
  }

  async function copyText(content: string) {
    try {
      await navigator.clipboard.writeText(content);
    } catch {
      // Ignore clipboard failures
    }
  }

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    const chatBody = document.querySelector(".chat-messages-container");
    if (chatBody) {
      chatBody.scrollTop = chatBody.scrollHeight;
    }
  }, [messages.length]);

  return (
    <div className="chat-workspace">
      {/* Left Sidebar - Session History */}
      <aside className="chat-sidebar">
        <div className="chat-sidebar__header">
          <button
            className="chat-sidebar__new-btn"
            type="button"
            disabled={createSessionMutation.isPending}
            onClick={() => createSessionMutation.mutate()}
          >
            <Plus size={18} strokeWidth={2} />
            <span>新建对话</span>
          </button>
        </div>

        <div className="chat-sidebar__list">
          {sessionsQuery.isLoading ? (
            <div className="chat-sidebar__loading">加载中...</div>
          ) : sessions.length === 0 ? (
            <div className="chat-sidebar__empty">
              <MessageCircleMore size={32} strokeWidth={1.5} opacity={0.3} />
              <p>还没有对话</p>
            </div>
          ) : (
            sessions.map((session) => (
              <SessionItem
                key={session.id}
                session={session}
                active={session.id === sessionId}
                deletePending={
                  deleteSessionMutation.isPending && deleteSessionMutation.variables === session.id
                }
                onDelete={() => deleteSessionMutation.mutate(session.id)}
              />
            ))
          )}
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="chat-main">
        {!sessionId ? (
          // Empty state - no session selected
          <div className="chat-empty">
            <div className="chat-empty__content">
              <div className="chat-empty__icon">
                <Sparkles size={48} strokeWidth={1.5} />
              </div>
              <h2>开始新的对话</h2>
              <p>点击左侧"新建对话"按钮，或选择一个历史对话继续聊天</p>
            </div>
          </div>
        ) : overviewQuery.isError ? (
          <StatusCard
            title="会话加载失败"
            description={
              overviewQuery.error instanceof Error
                ? overviewQuery.error.message
                : "请检查会话 ID 或网络连接"
            }
            tone="danger"
          />
        ) : overview ? (
          <>
            {/* Top Bar */}
            <header className="chat-header">
              <div className="chat-header__left">
                {isRenaming ? (
                  <form
                    className="chat-header__rename-form"
                    onSubmit={(event) => {
                      event.preventDefault();
                      const next = renameDraft.trim();
                      if (!next || renameMutation.isPending) {
                        return;
                      }
                      renameMutation.mutate(next);
                    }}
                  >
                    <input
                      value={renameDraft}
                      onChange={(event) => setRenameDraft(event.target.value)}
                      placeholder="输入会话名称"
                      autoFocus
                    />
                    <button
                      className="button button--primary button--sm"
                      type="submit"
                      disabled={!renameDraft.trim()}
                    >
                      <Save size={14} strokeWidth={2} />
                    </button>
                  </form>
                ) : (
                  <button
                    className="chat-header__title-btn"
                    type="button"
                    onClick={() => {
                      setRenameDraft(overview.session.name);
                      setIsRenaming(true);
                    }}
                  >
                    <span>{overview.session.name}</span>
                    <ChevronDown size={16} strokeWidth={1.9} />
                  </button>
                )}
              </div>

              <div className="chat-header__right">
                <select
                  className="chat-header__model-select"
                  value={overview.session.model_name || ""}
                  onChange={(event) => updateModelMutation.mutate(event.target.value)}
                >
                  <option value="">默认模型</option>
                  <option value="openai:gpt-5.4">GPT-5.4</option>
                  <option value="openai:gpt-5.2">GPT-5.2</option>
                  <option value="mock:default">Mock</option>
                </select>

                <button
                  className="chat-header__icon-btn"
                  type="button"
                  onClick={() =>
                    setSelectedPromptMessageId(messages[messages.length - 1]?.id ?? null)
                  }
                  disabled={messages.length === 0}
                  title="查看 Prompt"
                >
                  <PanelRightOpen size={18} strokeWidth={1.9} />
                </button>

                <button
                  className="chat-header__icon-btn"
                  type="button"
                  onClick={() => {
                    setRenameDraft(overview.session.name);
                    setIsRenaming(true);
                  }}
                  title="重命名"
                >
                  <Pencil size={18} strokeWidth={1.9} />
                </button>
              </div>
            </header>

            {/* Messages Area */}
            <div className="chat-messages-container">
              {messagesQuery.isLoading ? (
                <div className="chat-messages__loading">
                  <div className="loading-spinner" />
                  <p>加载消息中...</p>
                </div>
              ) : messagesQuery.isError ? (
                <StatusCard
                  title="消息加载失败"
                  description={
                    messagesQuery.error instanceof Error
                      ? messagesQuery.error.message
                      : "请检查网络连接"
                  }
                  tone="danger"
                />
              ) : messages.length === 0 ? (
                <div className="chat-messages__empty">
                  <div className="chat-messages__empty-icon">
                    <Bot size={40} strokeWidth={1.5} />
                  </div>
                  <h3>{overview.assistant_profile.name}</h3>
                  <p>{overview.assistant_profile.title}</p>
                  <p className="chat-messages__empty-hint">输入消息开始对话</p>
                </div>
              ) : (
                <div className="chat-messages">
                  {messages.map((message) => (
                    <MessageBubble
                      key={message.id}
                      message={message}
                      assistantName={overview.assistant_profile.name}
                      onCopy={() => copyText(message.content)}
                      onRollback={() => rollbackMutation.mutate(message.id)}
                      onShowPrompt={() => setSelectedPromptMessageId(message.id)}
                      rollbackPending={rollbackMutation.isPending}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Input Area */}
            <div className="chat-input-area">
              {quickReplyGroups.length > 0 && (
                <QuickReplies groups={quickReplyGroups} onPick={(content) => setDraft(content)} />
              )}

              <form className="chat-input-form" onSubmit={handleSend}>
                <div className="chat-input-wrapper">
                  <textarea
                    className="chat-input"
                    value={draft}
                    onChange={(event) => {
                      setDraft(event.target.value);
                      // Auto-resize textarea
                      event.target.style.height = 'auto';
                      event.target.style.height = event.target.scrollHeight + 'px';
                    }}
                    placeholder="输入消息... (Enter 发送，Shift+Enter 换行)"
                    rows={1}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        handleSend(event as any);
                      }
                    }}
                  />
                  <button
                    className="chat-send-btn"
                    type="submit"
                    disabled={!draft.trim() || sendMutation.isPending}
                    aria-label="发送"
                  >
                    <SendHorizonal size={20} strokeWidth={2} />
                  </button>
                </div>
                {latestTrace && (
                  <div className="chat-input-meta">
                    <span>{overview.assistant_profile.name}</span>
                    <span>·</span>
                    <span>{latestTrace.injection_count} 条注入</span>
                  </div>
                )}
              </form>
            </div>
          </>
        ) : null}
      </main>

      {/* Prompt Inspector Drawer */}
      {selectedPromptMessageId && (
        <>
          <div
            className="prompt-drawer-overlay"
            onClick={() => setSelectedPromptMessageId(null)}
          />
          <PromptDrawer
            trace={promptQuery.data ?? null}
            isLoading={promptQuery.isLoading}
            isError={promptQuery.isError}
            errorMessage={
              promptQuery.error instanceof Error
                ? promptQuery.error.message
                : "无法加载 Prompt 信息"
            }
            onClose={() => setSelectedPromptMessageId(null)}
            onCopy={async () => {
              if (promptQuery.data) {
                await copyText(buildPromptText(promptQuery.data));
              }
            }}
          />
        </>
      )}
    </div>
  );
}

function SessionItem({
  session,
  active,
  deletePending,
  onDelete,
}: {
  session: ChatSessionSummary;
  active: boolean;
  deletePending: boolean;
  onDelete: () => void;
}) {
  const navigate = useNavigate();

  return (
    <div className={`chat-session-item ${active ? "chat-session-item--active" : ""}`}>
      <button
        className="chat-session-item__link"
        type="button"
        onClick={() => navigate(`/chat/${session.id}`)}
      >
        <div className="chat-session-item__content">
          <h4>{session.name}</h4>
          <p>
            {session.message_count} 条消息 · {formatRelativeTime(session.updated_at)}
          </p>
        </div>
      </button>
      <button
        className="chat-session-item__delete"
        type="button"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          if (window.confirm(`确定要删除会话"${session.name}"吗？`)) {
            onDelete();
          }
        }}
        disabled={deletePending}
        title="删除会话"
      >
        <Trash2 size={14} strokeWidth={1.9} />
      </button>
    </div>
  );
}

function MessageBubble({
  message,
  assistantName,
  onCopy,
  onRollback,
  onShowPrompt,
  rollbackPending,
}: {
  message: Message;
  assistantName: string;
  onCopy: () => void;
  onRollback: () => void;
  onShowPrompt: () => void;
  rollbackPending: boolean;
}) {
  const isUser = message.role === "user";

  return (
    <div className={`message-bubble ${isUser ? "message-bubble--user" : "message-bubble--assistant"}`}>
      {!isUser && (
        <div className="message-bubble__avatar">
          <Bot size={20} strokeWidth={1.9} />
        </div>
      )}

      <div className="message-bubble__content">
        {!isUser && (
          <div className="message-bubble__header">
            <span className="message-bubble__name">{assistantName}</span>
            <time className="message-bubble__time">{formatDateTime(message.created_at)}</time>
          </div>
        )}

        <div className="message-bubble__text">{message.content}</div>

        <div className="message-bubble__actions">
          <button className="message-action-btn" type="button" onClick={onShowPrompt} title="查看 Prompt">
            Prompt
          </button>
          <button className="message-action-btn" type="button" onClick={onCopy} title="复制">
            <Copy size={14} strokeWidth={1.9} />
          </button>
          <button
            className="message-action-btn"
            type="button"
            onClick={onRollback}
            disabled={rollbackPending}
            title="回溯到此处"
          >
            <RotateCcw size={14} strokeWidth={1.9} />
          </button>
        </div>
      </div>
    </div>
  );
}

function QuickReplies({
  groups,
  onPick,
}: {
  groups: ChatQuickReplyGroup[];
  onPick: (content: string) => void;
}) {
  const items = groups
    .flatMap((group) => group.items.map((item) => ({ ...item, group: group.name })))
    .slice(0, 6);

  return (
    <div className="quick-replies">
      {items.map((item) => (
        <button
          key={item.id}
          className="quick-reply-chip"
          type="button"
          onClick={() => onPick(item.content)}
          title={item.group}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

function PromptDrawer({
  trace,
  isLoading,
  isError,
  errorMessage,
  onClose,
  onCopy,
}: {
  trace: PromptTraceInspector | null;
  isLoading: boolean;
  isError: boolean;
  errorMessage: string;
  onClose: () => void;
  onCopy: () => void;
}) {
  return (
    <aside className="prompt-drawer">
      <div className="prompt-drawer__header">
        <div>
          <h3>Prompt Inspector</h3>
          <p>查看这条消息的完整 Prompt 组装结果</p>
        </div>
        <div className="prompt-drawer__actions">
          <button className="button button--ghost button--sm" type="button" onClick={onCopy} disabled={!trace}>
            <Copy size={14} strokeWidth={1.9} />
            <span>复制</span>
          </button>
          <button className="button button--ghost button--sm" type="button" onClick={onClose}>
            关闭
          </button>
        </div>
      </div>

      <div className="prompt-drawer__body">
        {isLoading && <div className="prompt-drawer__loading">加载中...</div>}
        {isError && <StatusCard title="加载失败" description={errorMessage} tone="danger" />}

        {trace && (
          <div className="prompt-drawer__content">
            <div className="prompt-drawer__section">
              <h4>请求信息</h4>
              <dl className="prompt-drawer__dl">
                <dt>Provider</dt>
                <dd>{trace.request_section.provider_name || "mock"}</dd>
                <dt>模型</dt>
                <dd>{trace.request_section.requested_model || "默认"}</dd>
                <dt>注入项</dt>
                <dd>{trace.injection_count}</dd>
              </dl>
            </div>

            <div className="prompt-drawer__section">
              <h4>用户输入</h4>
              <pre className="prompt-drawer__code">
                {trace.normalized_input || trace.raw_user_input || "无"}
              </pre>
            </div>

            <div className="prompt-drawer__section">
              <h4>最终消息序列</h4>
              <pre className="prompt-drawer__code">{buildPromptText(trace)}</pre>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

function buildPromptText(trace: PromptTraceInspector): string {
  if (!trace.final_messages || trace.final_messages.length === 0) {
    return trace.normalized_input || trace.raw_user_input || "无 Prompt 内容";
  }

  return trace.final_messages
    .map((message, index) => {
      const role = typeof message.role === "string" ? message.role : `message_${index + 1}`;
      const content =
        typeof message.content === "string" ? message.content : JSON.stringify(message, null, 2);
      return `[${role}]\n${content}`;
    })
    .join("\n\n");
}
