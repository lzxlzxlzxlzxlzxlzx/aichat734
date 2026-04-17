import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, Clock3, MessageCircleMore, Plus, Sparkles } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { PageSection } from "../../../components/common/PageSection";
import { StatusCard } from "../../../components/common/StatusCard";
import {
  createChatSession,
  listChatSessions,
  listRecentCards,
  type ChatRecentCard,
  type ChatSessionSummary,
} from "../../../lib/api/chat";
import { formatDateTime, formatRelativeTime } from "../../../lib/format";

export function ChatHomePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const sessionsQuery = useQuery({
    queryKey: ["chat", "sessions"],
    queryFn: listChatSessions,
  });
  const recentCardsQuery = useQuery({
    queryKey: ["chat", "recent-cards"],
    queryFn: () => listRecentCards(8),
  });
  const createSessionMutation = useMutation({
    mutationFn: () => createChatSession({}),
    onSuccess: async (session) => {
      await queryClient.invalidateQueries({ queryKey: ["chat", "sessions"] });
      navigate(`/chat/session/${session.id}`);
    },
  });

  const sessions = sessionsQuery.data ?? [];
  const recentCards = recentCardsQuery.data ?? [];

  return (
    <div className="page-stack">
      <PageSection
        title="聊天模式首页"
        description="这里更接近日常 AI 聊天体验，强调会话切换、最近角色卡引用和长程对话的轻量工作流。"
      >
        <div className="chat-home-hero">
          <div className="play-home-hero__copy">
            <div className="pill-label">
              <Sparkles size={16} strokeWidth={1.8} />
              <span>主聊天工作区</span>
            </div>
            <h3>像主流 AI 产品一样开始对话，再自然地引用角色。</h3>
            <p>
              当前首页已接入真实聊天会话列表和最近角色卡。后续会继续补欢迎页推荐、搜索和更多设置入口。
            </p>
          </div>
          <div className="action-stack">
            <button
              className="button button--primary"
              type="button"
              disabled={createSessionMutation.isPending}
              onClick={() => createSessionMutation.mutate()}
            >
              <Plus size={16} strokeWidth={1.9} />
              <span>{createSessionMutation.isPending ? "正在创建..." : "新建聊天会话"}</span>
            </button>
            {sessions[0] ? (
              <Link className="button button--ghost" to={`/chat/session/${sessions[0].id}`}>
                <MessageCircleMore size={16} strokeWidth={1.9} />
                <span>继续最近会话</span>
              </Link>
            ) : null}
          </div>
        </div>

        <div className="chat-home-grid">
          <section className="detail-panel">
            <div className="section-heading">
              <div>
                <h3>聊天会话</h3>
                <p>按更新时间排序，作为聊天模式的主入口。</p>
              </div>
            </div>
            {sessionsQuery.isLoading ? <div className="detail-skeleton" /> : null}
            {sessionsQuery.isError ? (
              <StatusCard
                title="聊天会话加载失败"
                description={
                  sessionsQuery.error instanceof Error
                    ? sessionsQuery.error.message
                    : "请检查 chat 接口是否可用。"
                }
                tone="danger"
              />
            ) : null}
            {!sessionsQuery.isLoading && !sessionsQuery.isError && sessions.length === 0 ? (
              <StatusCard
                title="还没有聊天会话"
                description="点击上方的新建聊天会话，先创建第一段对话。"
              />
            ) : null}
            {!sessionsQuery.isLoading && !sessionsQuery.isError && sessions.length > 0 ? (
              <div className="chat-session-list">
                {sessions.map((session) => (
                  <ChatSessionCard key={session.id} session={session} />
                ))}
              </div>
            ) : null}
          </section>

          <section className="detail-panel">
            <div className="section-heading">
              <div>
                <h3>最近使用角色卡</h3>
                <p>方便在聊天模式中快速引用曾经游玩或创作过的角色。</p>
              </div>
            </div>
            {recentCardsQuery.isLoading ? <div className="detail-skeleton" /> : null}
            {recentCardsQuery.isError ? (
              <StatusCard
                title="最近角色卡加载失败"
                description={
                  recentCardsQuery.error instanceof Error
                    ? recentCardsQuery.error.message
                    : "请检查 recent cards 接口。"
                }
                tone="danger"
              />
            ) : null}
            {!recentCardsQuery.isLoading && !recentCardsQuery.isError && recentCards.length === 0 ? (
              <StatusCard
                title="最近没有角色引用记录"
                description="等你在游玩或创作模式中使用角色卡后，这里会开始出现最近记录。"
              />
            ) : null}
            {!recentCardsQuery.isLoading && !recentCardsQuery.isError && recentCards.length > 0 ? (
              <div className="recent-card-list">
                {recentCards.map((card) => (
                  <RecentCardCard key={card.id} card={card} />
                ))}
              </div>
            ) : null}
          </section>
        </div>
      </PageSection>
    </div>
  );
}

function ChatSessionCard({ session }: { session: ChatSessionSummary }) {
  return (
    <article className="session-summary-card">
      <div className="session-summary-card__head">
        <div>
          <h4>{session.name}</h4>
          <p>{session.status === "active" ? "进行中" : session.status}</p>
        </div>
        <Link className="button button--ghost" to={`/chat/session/${session.id}`}>
          <MessageCircleMore size={16} strokeWidth={1.9} />
          <span>进入会话</span>
        </Link>
      </div>
      <div className="session-summary-card__meta">
        <span>
          <Bot size={14} strokeWidth={1.9} />
          {session.model_name || "默认模型"}
        </span>
        <span>
          <Clock3 size={14} strokeWidth={1.9} />
          {formatRelativeTime(session.updated_at)}
        </span>
      </div>
      <div className="session-summary-card__footer">
        <span>{session.message_count} 条消息</span>
        <span>创建于 {formatDateTime(session.created_at)}</span>
      </div>
    </article>
  );
}

function RecentCardCard({ card }: { card: ChatRecentCard }) {
  return (
    <article className="recent-card-card">
      <div className="recent-card-card__avatar">{card.name.trim().slice(0, 1).toUpperCase()}</div>
      <div className="recent-card-card__body">
        <div>
          <h4>{card.name}</h4>
          <p>{card.description || "当前角色卡暂无简介。"}</p>
        </div>
        <div className="tag-row">
          {card.tags.length > 0 ? (
            card.tags.slice(0, 3).map((tag) => (
              <span key={tag} className="tag-chip">
                {tag}
              </span>
            ))
          ) : (
            <span className="tag-chip tag-chip--muted">暂无标签</span>
          )}
        </div>
        <div className="message-actions">
          <Link className="button button--ghost" to={`/play/${card.id}`}>
            角色详情
          </Link>
          {card.latest_session_id ? (
            <Link className="button button--ghost" to={`/play/session/${card.latest_session_id}`}>
              最近游玩
            </Link>
          ) : null}
        </div>
      </div>
    </article>
  );
}
