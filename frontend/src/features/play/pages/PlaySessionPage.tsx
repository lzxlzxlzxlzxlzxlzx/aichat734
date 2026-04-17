import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpenText,
  Bot,
  CircleDashed,
  Compass,
  CornerDownLeft,
  History,
  Lock,
  LockOpen,
  Pencil,
  RefreshCcw,
  SendHorizonal,
  Sparkles,
  Trash2,
  UserRound,
} from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { PageSection } from "../../../components/common/PageSection";
import { StatusCard } from "../../../components/common/StatusCard";
import {
  activateSwipe,
  deleteSwipe,
  listSessionMessages,
  regenerateMessage,
  rollbackFromMessage,
  sendSessionMessage,
  toggleMessageLock,
  type Message,
  updateMessage,
} from "../../../lib/api/messages";
import { getPlaySessionOverview } from "../../../lib/api/play";
import { getLatestSessionTrace } from "../../../lib/api/promptTraces";
import { listSessionSnapshots, restoreSnapshot } from "../../../lib/api/snapshots";
import { getSessionState } from "../../../lib/api/states";
import { formatDateTime, formatRelativeTime } from "../../../lib/format";

export function PlaySessionPage() {
  const { sessionId } = useParams();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const overviewQuery = useQuery({
    queryKey: ["play", "session-overview", sessionId],
    queryFn: () => getPlaySessionOverview(sessionId!),
    enabled: Boolean(sessionId),
  });
  const messagesQuery = useQuery({
    queryKey: ["session", "messages", sessionId],
    queryFn: () => listSessionMessages(sessionId!),
    enabled: Boolean(sessionId),
  });
  const stateQuery = useQuery({
    queryKey: ["session", "state", sessionId],
    queryFn: () => getSessionState(sessionId!),
    enabled: Boolean(sessionId),
  });
  const traceQuery = useQuery({
    queryKey: ["session", "trace-latest", sessionId],
    queryFn: () => getLatestSessionTrace(sessionId!),
    enabled: Boolean(sessionId),
  });
  const snapshotsQuery = useQuery({
    queryKey: ["session", "snapshots", sessionId],
    queryFn: () => listSessionSnapshots(sessionId!),
    enabled: Boolean(sessionId),
  });

  async function refreshSessionQueries() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["session", "messages", sessionId] }),
      queryClient.invalidateQueries({ queryKey: ["play", "session-overview", sessionId] }),
      queryClient.invalidateQueries({ queryKey: ["session", "state", sessionId] }),
      queryClient.invalidateQueries({ queryKey: ["session", "trace-latest", sessionId] }),
      queryClient.invalidateQueries({ queryKey: ["session", "snapshots", sessionId] }),
    ]);
  }

  const sendMutation = useMutation({
    mutationFn: (content: string) =>
      sendSessionMessage(sessionId!, {
        content,
      }),
    onSuccess: async () => {
      setDraft("");
      await refreshSessionQueries();
    },
  });
  const editMutation = useMutation({
    mutationFn: ({ messageId, content }: { messageId: string; content: string }) =>
      updateMessage(messageId, { content }),
    onSuccess: refreshSessionQueries,
  });
  const regenerateMutation = useMutation({
    mutationFn: (messageId: string) => regenerateMessage(messageId),
    onSuccess: refreshSessionQueries,
  });
  const rollbackMutation = useMutation({
    mutationFn: (messageId: string) => rollbackFromMessage(sessionId!, messageId),
    onSuccess: refreshSessionQueries,
  });
  const lockMutation = useMutation({
    mutationFn: ({ messageId, isLocked }: { messageId: string; isLocked: boolean }) =>
      toggleMessageLock(messageId, isLocked),
    onSuccess: refreshSessionQueries,
  });
  const activateSwipeMutation = useMutation({
    mutationFn: ({ messageId, swipeId }: { messageId: string; swipeId: string }) =>
      activateSwipe(messageId, swipeId),
    onSuccess: refreshSessionQueries,
  });
  const deleteSwipeMutation = useMutation({
    mutationFn: ({ messageId, swipeId }: { messageId: string; swipeId: string }) =>
      deleteSwipe(messageId, swipeId),
    onSuccess: refreshSessionQueries,
  });
  const restoreSnapshotMutation = useMutation({
    mutationFn: (snapshotId: string) => restoreSnapshot(sessionId!, snapshotId),
    onSuccess: refreshSessionQueries,
  });

  const displayMessages = useMemo(() => messagesQuery.data ?? [], [messagesQuery.data]);
  const latestVisibleMessageId = displayMessages.length > 0 ? displayMessages[displayMessages.length - 1]?.id : null;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || sendMutation.isPending) {
      return;
    }
    sendMutation.mutate(content);
  }

  if (!sessionId) {
    return (
      <div className="page-stack">
        <StatusCard title="会话不存在" description="当前缺少会话 ID。" tone="danger" />
      </div>
    );
  }

  return (
    <div className="page-stack">
      <PageSection
        title="游玩会话页"
        description="这一页已经接入会话概览、消息列表、发送消息、状态摘要和最新 trace 信息，是游玩主链路的第一版联调界面。"
      >
        {overviewQuery.isError ? (
          <StatusCard
            title="会话概览加载失败"
            description={
              overviewQuery.error instanceof Error
                ? overviewQuery.error.message
                : "请检查会话 ID 和后端服务。"
            }
            tone="danger"
          />
        ) : null}

        {overviewQuery.isLoading ? <div className="detail-skeleton" /> : null}

        {overviewQuery.data ? (
          <div className="play-session-layout">
            <aside className="play-session-sidebar">
              <section className="detail-panel">
                <div className="pill-label">
                  <Compass size={16} strokeWidth={1.8} />
                  <span>当前游玩</span>
                </div>
                <h3>{overviewQuery.data.card.name}</h3>
                <p>{overviewQuery.data.card.description || "当前角色卡暂无简介。"}</p>
                <div className="tag-row">
                  {overviewQuery.data.card.tags.length > 0 ? (
                    overviewQuery.data.card.tags.map((tag) => (
                      <span key={tag} className="tag-chip">
                        {tag}
                      </span>
                    ))
                  ) : (
                    <span className="tag-chip tag-chip--muted">暂无标签</span>
                  )}
                </div>
                <dl className="meta-list meta-list--stacked">
                  <div>
                    <dt>会话名称</dt>
                    <dd>{overviewQuery.data.session.name}</dd>
                  </div>
                  <div>
                    <dt>消息数</dt>
                    <dd>{overviewQuery.data.session.message_count}</dd>
                  </div>
                  <div>
                    <dt>最后更新</dt>
                    <dd>{formatRelativeTime(overviewQuery.data.session.updated_at)}</dd>
                  </div>
                  <div>
                    <dt>模型</dt>
                    <dd>{overviewQuery.data.session.model_name || "默认模型"}</dd>
                  </div>
                </dl>
                <div className="action-stack">
                  <Link className="button button--ghost" to={`/play/${overviewQuery.data.card.id}`}>
                    <CornerDownLeft size={16} strokeWidth={1.9} />
                    <span>返回角色详情</span>
                  </Link>
                  <Link className="button button--ghost" to={`/creation/card/${overviewQuery.data.card.id}`}>
                    <BookOpenText size={16} strokeWidth={1.9} />
                    <span>查看创作页</span>
                  </Link>
                </div>
              </section>

              <section className="detail-panel">
                <div className="section-heading">
                  <div>
                    <h3>状态摘要</h3>
                    <p>这里先展示会话的当前状态概况，后续再扩展为完整状态面板。</p>
                  </div>
                </div>
                <p className="state-summary-text">
                  {overviewQuery.data.state_summary || "当前还没有提取到状态摘要。"}
                </p>
                {stateQuery.data ? (
                  <div className="state-chip-list">
                    {Object.entries(stateQuery.data.variables).slice(0, 8).map(([key, value]) => (
                      <div key={key} className="state-chip">
                        <span>{key}</span>
                        <strong>{String(value)}</strong>
                      </div>
                    ))}
                  </div>
                ) : null}
              </section>

              <section className="detail-panel">
                <div className="section-heading">
                  <div>
                    <h3>最新 Trace</h3>
                    <p>这一块先接入最新一次生成的摘要信息，后续再做完整 Inspector 抽屉。</p>
                  </div>
                </div>
                {traceQuery.isLoading ? (
                  <p className="muted-copy">正在读取最新 trace...</p>
                ) : null}
                {traceQuery.isError ? (
                  <p className="inline-error">
                    {traceQuery.error instanceof Error
                      ? traceQuery.error.message
                      : "无法读取最新 trace。"}
                  </p>
                ) : null}
                {traceQuery.data ? (
                  <div className="trace-summary">
                    <div className="trace-summary__row">
                      <span>Provider</span>
                      <strong>{traceQuery.data.request_section.provider_name || "mock"}</strong>
                    </div>
                    <div className="trace-summary__row">
                      <span>模型</span>
                      <strong>{traceQuery.data.request_section.requested_model || "默认"}</strong>
                    </div>
                    <div className="trace-summary__row">
                      <span>注入项</span>
                      <strong>{traceQuery.data.injection_count}</strong>
                    </div>
                    <div className="trace-summary__row">
                      <span>最终消息数</span>
                      <strong>{traceQuery.data.final_message_count}</strong>
                    </div>
                    <div className="trace-summary__row">
                      <span>状态更新</span>
                      <strong>{traceQuery.data.overview.has_state_update ? "有" : "无"}</strong>
                    </div>
                    <div className="trace-summary__row">
                      <span>生成时间</span>
                      <strong>{formatDateTime(traceQuery.data.created_at)}</strong>
                    </div>
                  </div>
                ) : null}
              </section>

              <section className="detail-panel">
                <div className="section-heading">
                  <div>
                    <h3>快照恢复</h3>
                    <p>当前显示最近生成的回溯或编辑快照，可用于快速恢复对话分叉点。</p>
                  </div>
                </div>
                {snapshotsQuery.isLoading ? <p className="muted-copy">正在读取快照...</p> : null}
                {snapshotsQuery.isError ? (
                  <p className="inline-error">
                    {snapshotsQuery.error instanceof Error
                      ? snapshotsQuery.error.message
                      : "无法读取快照列表。"}
                  </p>
                ) : null}
                {snapshotsQuery.data && snapshotsQuery.data.length > 0 ? (
                  <div className="snapshot-list">
                    {snapshotsQuery.data.slice(0, 6).map((snapshot) => (
                      <div key={snapshot.id} className="snapshot-card">
                        <div className="snapshot-card__head">
                          <strong>{snapshot.label || snapshot.snapshot_type}</strong>
                          <span>{formatDateTime(snapshot.created_at)}</span>
                        </div>
                        <p>
                          序号 {snapshot.message_sequence}
                          {snapshot.message_id ? ` · 关联消息 ${snapshot.message_id.slice(0, 8)}` : ""}
                        </p>
                        <button
                          className="button button--ghost"
                          type="button"
                          disabled={restoreSnapshotMutation.isPending}
                          onClick={() => restoreSnapshotMutation.mutate(snapshot.id)}
                        >
                          <History size={16} strokeWidth={1.9} />
                          <span>恢复到此快照</span>
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  !snapshotsQuery.isLoading && (
                    <StatusCard
                      title="当前还没有快照"
                      description="当你编辑消息、回溯或触发回滚后，这里会出现可恢复的快照记录。"
                    />
                  )
                )}
                {restoreSnapshotMutation.isError ? (
                  <p className="inline-error">
                    {restoreSnapshotMutation.error instanceof Error
                      ? restoreSnapshotMutation.error.message
                      : "恢复快照失败。"}
                  </p>
                ) : null}
              </section>
            </aside>

            <section className="play-session-main">
              <div className="session-stream">
                {messagesQuery.isLoading ? (
                  <div className="message-list">
                    {Array.from({ length: 4 }).map((_, index) => (
                      <div key={index} className="message-bubble message-bubble--loading" />
                    ))}
                  </div>
                ) : null}

                {messagesQuery.isError ? (
                  <StatusCard
                    title="消息加载失败"
                    description={
                      messagesQuery.error instanceof Error
                        ? messagesQuery.error.message
                        : "请检查消息链路接口是否正常。"
                    }
                    tone="danger"
                  />
                ) : null}

                {!messagesQuery.isLoading && !messagesQuery.isError && displayMessages.length === 0 ? (
                  <StatusCard
                    title="当前会话还没有消息"
                    description="你可以直接在下方输入，开始这段游玩会话。"
                  />
                ) : null}

                {!messagesQuery.isLoading && !messagesQuery.isError && displayMessages.length > 0 ? (
                  <div className="message-list">
                    {displayMessages.map((message) => (
                      <MessageBubble
                        key={message.id}
                        message={message}
                        isLatest={message.id === latestVisibleMessageId}
                        onEdit={(content) => editMutation.mutate({ messageId: message.id, content })}
                        onRegenerate={() => regenerateMutation.mutate(message.id)}
                        onRollback={() => rollbackMutation.mutate(message.id)}
                        onToggleLock={(isLocked) =>
                          lockMutation.mutate({ messageId: message.id, isLocked })
                        }
                        onActivateSwipe={(swipeId) =>
                          activateSwipeMutation.mutate({ messageId: message.id, swipeId })
                        }
                        onDeleteSwipe={(swipeId) =>
                          deleteSwipeMutation.mutate({ messageId: message.id, swipeId })
                        }
                        actionPending={
                          editMutation.isPending ||
                          regenerateMutation.isPending ||
                          rollbackMutation.isPending ||
                          lockMutation.isPending ||
                          activateSwipeMutation.isPending ||
                          deleteSwipeMutation.isPending
                        }
                      />
                    ))}
                  </div>
                ) : null}
              </div>

              <form className="composer" onSubmit={handleSubmit}>
                <label className="composer__input">
                  <textarea
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    placeholder="继续推进剧情，或给角色一个新的回应..."
                    rows={4}
                  />
                </label>
                <div className="composer__footer">
                  <div className="composer__hint">
                    当前先支持纯文本发送。下一步会继续接入回溯、重生成、swipe、附件与更多状态联动。
                  </div>
                  <button
                    className="button button--primary"
                    type="submit"
                    disabled={!draft.trim() || sendMutation.isPending}
                  >
                    <SendHorizonal size={16} strokeWidth={1.9} />
                    <span>{sendMutation.isPending ? "发送中..." : "发送消息"}</span>
                  </button>
                </div>
                {sendMutation.isError ? (
                  <p className="inline-error">
                    {sendMutation.error instanceof Error
                      ? sendMutation.error.message
                      : "发送消息失败。"}
                  </p>
                ) : null}
              </form>
            </section>
          </div>
        ) : null}
      </PageSection>
    </div>
  );
}

function MessageBubble({
  message,
  isLatest,
  onEdit,
  onRegenerate,
  onRollback,
  onToggleLock,
  onActivateSwipe,
  onDeleteSwipe,
  actionPending,
}: {
  message: Message;
  isLatest: boolean;
  onEdit: (content: string) => void;
  onRegenerate: () => void;
  onRollback: () => void;
  onToggleLock: (isLocked: boolean) => void;
  onActivateSwipe: (swipeId: string) => void;
  onDeleteSwipe: (swipeId: string) => void;
  actionPending: boolean;
}) {
  const isUser = message.role === "user";
  const Icon = isUser ? UserRound : Bot;
  const [isEditing, setIsEditing] = useState(false);
  const [editDraft, setEditDraft] = useState(message.content);

  const canEdit = isUser && !message.is_locked;
  const canRegenerate = !isUser && isLatest;
  const canRollback = !message.is_locked;
  const activeSwipeId = message.active_swipe_id;

  function handleEditSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = editDraft.trim();
    if (!next || actionPending) {
      return;
    }
    onEdit(next);
    setIsEditing(false);
  }

  return (
    <article
      className={isUser ? "message-bubble message-bubble--user" : "message-bubble message-bubble--assistant"}
    >
      <div className="message-bubble__avatar">
        <Icon size={18} strokeWidth={1.9} />
      </div>
      <div className="message-bubble__body">
        <div className="message-bubble__meta">
          <span>{isUser ? "你" : "角色回应"}</span>
          <span>{formatDateTime(message.created_at)}</span>
          {message.is_edited ? <span>已编辑</span> : null}
          {message.is_locked ? <span>已锁定</span> : null}
        </div>
        {isEditing ? (
          <form className="message-edit-form" onSubmit={handleEditSubmit}>
            <textarea
              value={editDraft}
              onChange={(event) => setEditDraft(event.target.value)}
              rows={5}
            />
            <div className="message-actions">
              <button className="button button--primary" type="submit" disabled={actionPending || !editDraft.trim()}>
                <Pencil size={16} strokeWidth={1.9} />
                <span>保存编辑</span>
              </button>
              <button
                className="button button--ghost"
                type="button"
                disabled={actionPending}
                onClick={() => {
                  setIsEditing(false);
                  setEditDraft(message.content);
                }}
              >
                取消
              </button>
            </div>
          </form>
        ) : (
          <div className="message-bubble__content">{message.content}</div>
        )}
        <div className="message-bubble__footer">
          <span>序号 #{message.sequence}</span>
          <span>来源 {message.source_type}</span>
          {message.swipes.length > 0 ? (
            <span className="message-bubble__swipe">
              <CircleDashed size={14} strokeWidth={1.9} />
              {message.swipes.length} 个 swipe
            </span>
          ) : null}
        </div>
        <div className="message-actions">
          {canEdit ? (
            <button
              className="button button--ghost"
              type="button"
              disabled={actionPending}
              onClick={() => setIsEditing((value) => !value)}
            >
              <Pencil size={16} strokeWidth={1.9} />
              <span>{isEditing ? "收起编辑" : "编辑消息"}</span>
            </button>
          ) : null}
          {canRegenerate ? (
            <button
              className="button button--ghost"
              type="button"
              disabled={actionPending}
              onClick={onRegenerate}
            >
              <RefreshCcw size={16} strokeWidth={1.9} />
              <span>重生成</span>
            </button>
          ) : null}
          {canRollback ? (
            <button
              className="button button--ghost"
              type="button"
              disabled={actionPending}
              onClick={onRollback}
            >
              <History size={16} strokeWidth={1.9} />
              <span>回溯到这里</span>
            </button>
          ) : null}
          <button
            className="button button--ghost"
            type="button"
            disabled={actionPending}
            onClick={() => onToggleLock(!message.is_locked)}
          >
            {message.is_locked ? <LockOpen size={16} strokeWidth={1.9} /> : <Lock size={16} strokeWidth={1.9} />}
            <span>{message.is_locked ? "取消锁定" : "锁定消息"}</span>
          </button>
        </div>
        {!isUser && message.swipes.length > 0 ? (
          <div className="swipe-panel">
            <div className="swipe-panel__title">Swipes</div>
            <div className="swipe-list">
              {message.swipes.map((swipe) => {
                const isActive = swipe.id === activeSwipeId;

                return (
                  <div
                    key={swipe.id}
                    className={isActive ? "swipe-card swipe-card--active" : "swipe-card"}
                  >
                    <div className="swipe-card__head">
                      <strong>#{swipe.swipe_index + 1}</strong>
                      <span>{swipe.model_name || "默认模型"}</span>
                    </div>
                    <p>{(swipe.display_response || swipe.raw_response || "").slice(0, 140) || "无内容"}</p>
                    <div className="message-actions">
                      {!isActive ? (
                        <button
                          className="button button--ghost"
                          type="button"
                          disabled={actionPending || !isLatest}
                          onClick={() => onActivateSwipe(swipe.id)}
                        >
                          <Sparkles size={16} strokeWidth={1.9} />
                          <span>切换为当前</span>
                        </button>
                      ) : (
                        <span className="soft-chip">当前使用中</span>
                      )}
                      {message.swipes.length > 1 ? (
                        <button
                          className="button button--ghost"
                          type="button"
                          disabled={actionPending}
                          onClick={() => onDeleteSwipe(swipe.id)}
                        >
                          <Trash2 size={16} strokeWidth={1.9} />
                          <span>删除</span>
                        </button>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}
      </div>
    </article>
  );
}
