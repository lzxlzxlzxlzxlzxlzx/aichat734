import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bot,
  ChevronDown,
  Copy,
  MessageCircleMore,
  PanelRightOpen,
  Pencil,
  RotateCcw,
  Save,
  SendHorizonal,
  Sparkles,
  Trash2,
} from "lucide-react";
import { FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

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

export function ChatSessionPage() {
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
      navigate(`/chat/session/${session.id}`);
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

  function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || sendMutation.isPending) {
      return;
    }
    sendMutation.mutate(content);
  }

  async function copyText(content: string) {
    try {
      await navigator.clipboard.writeText(content);
    } catch {
      // Ignore clipboard failures in unsupported environments.
    }
  }

  if (!sessionId) {
    return (
      <div className="page-stack">
        <StatusCard title="聊天会话不存在" description="当前缺少会话 ID。" tone="danger" />
      </div>
    );
  }

  return (
    <div className="chat-workspace chat-workspace--kimi">
      <aside className="chat-workspace__sidebar chat-sidebar-kimi">
        <div className="chat-sidebar-kimi__brand">
          <button
            className="chat-sidebar-kimi__new"
            type="button"
            disabled={createSessionMutation.isPending}
            onClick={() => createSessionMutation.mutate()}
          >
            <MessageCircleMore size={16} strokeWidth={1.9} />
            <span>{createSessionMutation.isPending ? "创建中..." : "新建会话"}</span>
          </button>
        </div>

        <div className="chat-sidebar-kimi__section">历史会话</div>
        <div className="chat-workspace__session-list chat-session-history">
          {(sessionsQuery.data ?? []).map((session) => (
            <ChatHistoryItem
              key={session.id}
              session={session}
              active={session.id === sessionId}
              deletePending={
                deleteSessionMutation.isPending &&
                deleteSessionMutation.variables === session.id
              }
              onDelete={() => deleteSessionMutation.mutate(session.id)}
            />
          ))}
        </div>
      </aside>

      <section className="chat-workspace__main chat-main-kimi">
        {overviewQuery.isError ? (
          <StatusCard
            title="聊天会话加载失败"
            description={
              overviewQuery.error instanceof Error
                ? overviewQuery.error.message
                : "请检查聊天接口或会话 ID。"
            }
            tone="danger"
          />
        ) : null}

        {overview ? (
          <>
            <header className="chat-topbar chat-topbar--kimi">
              <div className="chat-topbar__title chat-topbar__title--kimi">
                {isRenaming ? (
                  <form
                    className="rename-form"
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
                      placeholder="输入新的会话名称"
                    />
                    <button
                      className="button button--primary"
                      type="submit"
                      disabled={!renameDraft.trim()}
                    >
                      <Save size={16} strokeWidth={1.9} />
                      <span>保存</span>
                    </button>
                  </form>
                ) : (
                  <button
                    className="chat-title-trigger"
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

              <div className="chat-topbar__actions chat-topbar__actions--kimi">
                <select
                  className="model-select model-select--minimal"
                  value={overview.session.model_name || ""}
                  onChange={(event) => updateModelMutation.mutate(event.target.value)}
                >
                  <option value="">默认模型</option>
                  <option value="openai:gpt-5.4">openai:gpt-5.4</option>
                  <option value="openai:gpt-5.2">openai:gpt-5.2</option>
                  <option value="mock:default">mock:default</option>
                </select>

                <button
                  className="chat-icon-button"
                  type="button"
                  onClick={() => setSelectedPromptMessageId(messages[messages.length - 1]?.id ?? null)}
                  disabled={messages.length === 0}
                  title="查看最近一条消息的 Prompt"
                >
                  <PanelRightOpen size={16} strokeWidth={1.9} />
                </button>

                <button
                  className="chat-icon-button"
                  type="button"
                  onClick={() => {
                    setRenameDraft(overview.session.name);
                    setIsRenaming(true);
                  }}
                  title="重命名会话"
                >
                  <Pencil size={16} strokeWidth={1.9} />
                </button>
              </div>
            </header>

            <div className="chat-body chat-body--wide chat-body--kimi">
              <div className="chat-stream chat-stream--kimi">
                <div className="chat-stream__inner">
                  {messagesQuery.isLoading ? (
                    <div className="message-list">
                      {Array.from({ length: 3 }).map((_, index) => (
                        <div key={index} className="message-bubble message-bubble--loading" />
                      ))}
                    </div>
                  ) : null}

                  {messagesQuery.isError ? (
                    <StatusCard
                      title="聊天消息加载失败"
                      description={
                        messagesQuery.error instanceof Error
                          ? messagesQuery.error.message
                          : "请检查消息接口。"
                      }
                      tone="danger"
                    />
                  ) : null}

                  {!messagesQuery.isLoading && !messagesQuery.isError && messages.length === 0 ? (
                    <div className="chat-empty-state">
                      <div className="chat-empty-state__badge">
                        <Sparkles size={18} strokeWidth={1.9} />
                        <span>{overview.assistant_profile.name}</span>
                      </div>
                      <h2>开始一段新的对话</h2>
                      <p>直接输入消息，或者先点一个快捷回复。</p>
                    </div>
                  ) : null}

                  {!messagesQuery.isLoading && !messagesQuery.isError && messages.length > 0 ? (
                    <div className="message-list chat-message-list chat-message-list--kimi">
                      {messages.map((message) => (
                        <ChatMessageBubble
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
                  ) : null}
                </div>
              </div>
            </div>

            <div className="chat-composer-wrap">
              {quickReplyGroups.length > 0 ? (
                <QuickReplyGroups groups={quickReplyGroups} onPick={(content) => setDraft(content)} />
              ) : null}

              <form className="chat-composer chat-composer--kimi" onSubmit={handleSend}>
                <label className="chat-composer__input chat-composer__input--kimi">
                  <textarea
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    placeholder="问点难的，让我多想一步"
                    rows={3}
                  />
                </label>
                <div className="chat-composer__footer chat-composer__footer--kimi">
                  <div className="chat-composer__meta chat-composer__meta--kimi">
                    <span>{overview.assistant_profile.name}</span>
                    <span>{overview.assistant_profile.title}</span>
                    {latestTrace ? <span>{latestTrace.injection_count} 条注入</span> : null}
                  </div>
                  <button
                    className="chat-send-button"
                    type="submit"
                    disabled={!draft.trim() || sendMutation.isPending}
                    aria-label="发送消息"
                  >
                    <SendHorizonal size={18} strokeWidth={2} />
                  </button>
                </div>
              </form>
            </div>
          </>
        ) : null}
      </section>

      {selectedPromptMessageId ? (
        <>
          <button
            className="prompt-drawer__scrim"
            type="button"
            aria-label="关闭 Prompt 面板"
            onClick={() => setSelectedPromptMessageId(null)}
          />
          <PromptDrawer
            trace={promptQuery.data ?? null}
            isLoading={promptQuery.isLoading}
            isError={promptQuery.isError}
            errorMessage={
              promptQuery.error instanceof Error
                ? promptQuery.error.message
                : "这条消息暂时没有可读取的 Prompt。"
            }
            onClose={() => setSelectedPromptMessageId(null)}
            onCopy={async () => {
              if (!promptQuery.data) {
                return;
              }
              await copyText(buildPromptText(promptQuery.data));
            }}
          />
        </>
      ) : null}
    </div>
  );
}

function ChatHistoryItem({
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
  return (
    <div className={active ? "chat-session-link chat-session-link--active" : "chat-session-link"}>
      <Link className="chat-session-link__main" to={`/chat/session/${session.id}`}>
        <div className="chat-session-link__copy">
          <strong>{session.name}</strong>
          <p>{session.model_name || "默认模型"}</p>
        </div>
        <span className="chat-session-link__time">{formatRelativeTime(session.updated_at)}</span>
      </Link>
      <button
        className="chat-session-link__delete"
        type="button"
        onClick={onDelete}
        disabled={deletePending}
        title="删除会话"
        aria-label={`删除会话 ${session.name}`}
      >
        <Trash2 size={14} strokeWidth={1.9} />
      </button>
    </div>
  );
}

function ChatMessageBubble({
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

  if (isUser) {
    return (
      <article className="chat-message chat-message--kimi chat-message--user">
        <div className="chat-message__user-bubble">{message.content}</div>
        <div className="chat-message__actions chat-message__actions--user" aria-label="用户消息操作">
          <button className="button button--ghost" type="button" onClick={onShowPrompt}>
            Prompt
          </button>
          <button className="button button--ghost" type="button" onClick={onCopy}>
            <Copy size={15} strokeWidth={1.9} />
            <span>复制</span>
          </button>
          <button
            className="button button--ghost"
            type="button"
            disabled={rollbackPending}
            onClick={onRollback}
          >
            <RotateCcw size={15} strokeWidth={1.9} />
            <span>回溯</span>
          </button>
        </div>
      </article>
    );
  }

  return (
    <article className="chat-message chat-message--kimi chat-message--assistant">
      <div className="chat-message__assistant-row">
        <div className="chat-message__assistant-avatar">
          <Bot size={16} strokeWidth={1.9} />
        </div>
        <div className="chat-message__assistant-block">
          <div className="chat-message__assistant-head">
            <span className="chat-message__assistant-name">{assistantName}</span>
            <time>{formatDateTime(message.created_at)}</time>
          </div>
          <div className="chat-message__assistant-content">{message.content}</div>
          <div className="chat-message__actions chat-message__actions--assistant" aria-label="助手消息操作">
            <button className="button button--ghost" type="button" onClick={onShowPrompt}>
              Prompt
            </button>
            <button className="button button--ghost" type="button" onClick={onCopy}>
              <Copy size={15} strokeWidth={1.9} />
              <span>复制</span>
            </button>
            <button
              className="button button--ghost"
              type="button"
              disabled={rollbackPending}
              onClick={onRollback}
            >
              <RotateCcw size={15} strokeWidth={1.9} />
              <span>回溯</span>
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}

function QuickReplyGroups({
  groups,
  onPick,
}: {
  groups: ChatQuickReplyGroup[];
  onPick: (content: string) => void;
}) {
  const items = groups
    .flatMap((group) => group.items.map((item) => ({ ...item, group: group.name })))
    .slice(0, 8);

  return (
    <div className="quick-reply-groups quick-reply-groups--kimi">
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
      <div className="prompt-drawer__head">
        <div>
          <h2>本条消息 Prompt</h2>
          <p>这里展示这条消息对应的 Prompt 组装结果和关键上下文。</p>
        </div>
        <div className="message-actions">
          <button className="button button--ghost" type="button" onClick={onCopy} disabled={!trace}>
            <Copy size={15} strokeWidth={1.9} />
            <span>复制 Prompt</span>
          </button>
          <button className="button button--ghost" type="button" onClick={onClose}>
            关闭
          </button>
        </div>
      </div>

      {isLoading ? <div className="chat-rail__empty">正在读取 Prompt...</div> : null}
      {isError ? <StatusCard title="Prompt 读取失败" description={errorMessage} tone="danger" /> : null}

      {trace ? (
        <div className="prompt-drawer__content">
          <div className="prompt-drawer__block">
            <div className="prompt-drawer__label">请求信息</div>
            <div className="prompt-drawer__kv">
              <span>Provider</span>
              <strong>{trace.request_section.provider_name || "mock"}</strong>
            </div>
            <div className="prompt-drawer__kv">
              <span>模型</span>
              <strong>{trace.request_section.requested_model || "默认"}</strong>
            </div>
            <div className="prompt-drawer__kv">
              <span>注入项</span>
              <strong>{trace.injection_count}</strong>
            </div>
          </div>

          <div className="prompt-drawer__block">
            <div className="prompt-drawer__label">输入</div>
            <pre>{trace.normalized_input || trace.raw_user_input || "无"}</pre>
          </div>

          <div className="prompt-drawer__block">
            <div className="prompt-drawer__label">最终消息序列</div>
            <pre>{buildPromptText(trace)}</pre>
          </div>
        </div>
      ) : null}
    </aside>
  );
}

function buildPromptText(trace: PromptTraceInspector) {
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
