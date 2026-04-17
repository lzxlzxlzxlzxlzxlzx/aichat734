import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Clock3,
  CopyPlus,
  FilePenLine,
  MessageCircleMore,
  Play,
  Sparkles,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { PageSection } from "../../../components/common/PageSection";
import { StatusCard } from "../../../components/common/StatusCard";
import {
  createPlaySession,
  getPlayCardDetail,
  type PlayOpeningOption,
  type PlaySessionSummary,
} from "../../../lib/api/play";
import { formatDateTime, formatRelativeTime } from "../../../lib/format";

export function PlayCardDetailPage() {
  const { cardId } = useParams();
  const navigate = useNavigate();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["play", "card-detail", cardId],
    queryFn: () => getPlayCardDetail(cardId!),
    enabled: Boolean(cardId),
  });

  const createSessionMutation = useMutation({
    mutationFn: ({
      openingIndex,
      reuseLatest,
    }: {
      openingIndex?: number;
      reuseLatest?: boolean;
    }) =>
      createPlaySession(cardId!, {
        name: `${data?.card.name ?? "新游玩会话"} ${new Date().toLocaleString("zh-CN")}`,
        opening_index: openingIndex,
        use_latest_existing_session: reuseLatest,
      }),
    onSuccess: (response) => {
      navigate(`/play/session/${response.session.id}`);
    },
  });

  if (!cardId) {
    return (
      <div className="page-stack">
        <StatusCard title="角色卡不存在" description="当前缺少角色卡 ID。" tone="danger" />
      </div>
    );
  }

  return (
    <div className="page-stack">
      <PageSection
        title="角色卡详情页"
        description="在这里查看角色的开场选项、最近游玩会话，并决定是开始新会话还是继续上一次进度。"
      >
        {isLoading ? <div className="detail-skeleton" /> : null}

        {isError ? (
          <StatusCard
            title="角色卡详情加载失败"
            description={error instanceof Error ? error.message : "请检查后端服务和当前角色卡是否存在。"}
            tone="danger"
          />
        ) : null}

        {!isLoading && !isError && data ? (
          <>
            <div className="detail-hero">
              <div className="detail-hero__identity">
                <div className="detail-hero__avatar">
                  {data.card.name.trim().slice(0, 1).toUpperCase()}
                </div>
                <div className="detail-hero__copy">
                  <div className="pill-label">
                    <Sparkles size={16} strokeWidth={1.8} />
                    <span>游玩角色卡</span>
                  </div>
                  <h3>{data.card.name}</h3>
                  <p>
                    {data.card.description?.trim() ||
                      "当前角色卡暂无简介。后续创作模式中可以继续补全更多设定信息。"}
                  </p>
                  <div className="tag-row">
                    {data.card.tags.length > 0 ? (
                      data.card.tags.map((tag) => (
                        <span key={tag} className="tag-chip">
                          {tag}
                        </span>
                      ))
                    ) : (
                      <span className="tag-chip tag-chip--muted">暂无标签</span>
                    )}
                  </div>
                </div>
              </div>

              <div className="detail-hero__side">
                <dl className="meta-list meta-list--stacked">
                  <div>
                    <dt>开场数量</dt>
                    <dd>{data.openings.length}</dd>
                  </div>
                  <div>
                    <dt>最近会话数</dt>
                    <dd>{data.sessions.length}</dd>
                  </div>
                  <div>
                    <dt>发布时间</dt>
                    <dd>{formatDateTime(data.card.published_at)}</dd>
                  </div>
                </dl>
                <div className="action-stack">
                  <button
                    className="button button--primary"
                    type="button"
                    disabled={createSessionMutation.isPending}
                    onClick={() => createSessionMutation.mutate({})}
                  >
                    <Play size={16} strokeWidth={1.9} />
                    <span>{createSessionMutation.isPending ? "正在创建..." : "开始新游玩"}</span>
                  </button>
                  {data.card.latest_session_id ? (
                    <Link
                      className="button button--ghost"
                      to={`/play/session/${data.card.latest_session_id}`}
                    >
                      <MessageCircleMore size={16} strokeWidth={1.9} />
                      <span>继续最近会话</span>
                    </Link>
                  ) : null}
                  <Link className="button button--ghost" to={`/creation/card/${data.card.id}`}>
                    <FilePenLine size={16} strokeWidth={1.9} />
                    <span>进入创作模式</span>
                  </Link>
                </div>
                {createSessionMutation.isError ? (
                  <p className="inline-error">
                    {createSessionMutation.error instanceof Error
                      ? createSessionMutation.error.message
                      : "创建游玩会话失败。"}
                  </p>
                ) : null}
              </div>
            </div>

            <div className="detail-grid">
              <section className="detail-panel">
                <div className="section-heading">
                  <div>
                    <h3>开场选择</h3>
                    <p>你可以直接使用默认开场，也可以从其他候选开场进入不同的初始语境。</p>
                  </div>
                </div>
                {data.openings.length > 0 ? (
                  <div className="opening-list">
                    {data.openings.map((opening) => (
                      <OpeningCard
                        key={opening.index}
                        opening={opening}
                        isPending={createSessionMutation.isPending}
                        onStart={() =>
                          createSessionMutation.mutate({ openingIndex: opening.index })
                        }
                      />
                    ))}
                  </div>
                ) : (
                  <StatusCard
                    title="当前没有预设开场"
                    description="仍然可以直接创建游玩会话，后续由用户输入开启对话。"
                  />
                )}
              </section>

              <section className="detail-panel">
                <div className="section-heading">
                  <div>
                    <h3>最近游玩会话</h3>
                    <p>支持继续最近会话，或复制当前对话在后续会话页进行分线式探索。</p>
                  </div>
                </div>
                {data.sessions.length > 0 ? (
                  <div className="session-summary-list">
                    {data.sessions.map((session) => (
                      <SessionSummaryCard key={session.id} session={session} />
                    ))}
                  </div>
                ) : (
                  <StatusCard
                    title="还没有游玩记录"
                    description="可以从上方直接开始第一段游玩会话。"
                  />
                )}
              </section>
            </div>
          </>
        ) : null}
      </PageSection>
    </div>
  );
}

function OpeningCard({
  opening,
  isPending,
  onStart,
}: {
  opening: PlayOpeningOption;
  isPending: boolean;
  onStart: () => void;
}) {
  return (
    <article className="opening-card">
      <div className="opening-card__head">
        <div>
          <h4>{opening.title}</h4>
          <p>{opening.is_default ? "默认开场" : `候选开场 #${opening.index}`}</p>
        </div>
        <button className="button button--ghost" type="button" disabled={isPending} onClick={onStart}>
          <Play size={16} strokeWidth={1.9} />
          <span>从此开场进入</span>
        </button>
      </div>
      <p className="opening-card__content">{opening.content}</p>
    </article>
  );
}

function SessionSummaryCard({ session }: { session: PlaySessionSummary }) {
  return (
    <article className="session-summary-card">
      <div className="session-summary-card__head">
        <div>
          <h4>{session.name}</h4>
          <p>{session.status === "active" ? "进行中" : session.status}</p>
        </div>
        <Link className="button button--ghost" to={`/play/session/${session.id}`}>
          <ArrowRight size={16} strokeWidth={1.9} />
          <span>进入会话</span>
        </Link>
      </div>
      <div className="session-summary-card__meta">
        <span>
          <MessageCircleMore size={14} strokeWidth={1.9} />
          {session.message_count} 条消息
        </span>
        <span>
          <Clock3 size={14} strokeWidth={1.9} />
          {formatRelativeTime(session.updated_at)}
        </span>
        {session.model_name ? (
          <span>
            <CopyPlus size={14} strokeWidth={1.9} />
            {session.model_name}
          </span>
        ) : null}
      </div>
      <div className="session-summary-card__footer">
        <span>创建于 {formatDateTime(session.created_at)}</span>
        <span>最后更新 {formatDateTime(session.updated_at)}</span>
      </div>
    </article>
  );
}
