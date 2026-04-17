import { useDeferredValue, useMemo, useState } from "react";
import { Compass, MessageCircleMore, Search, Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { PageSection } from "../../../components/common/PageSection";
import { StatusCard } from "../../../components/common/StatusCard";
import { listPlayCards, type PlayCardSummary } from "../../../lib/api/play";
import { formatDateTime, formatRelativeTime } from "../../../lib/format";

export function PlayHomePage() {
  const [searchText, setSearchText] = useState("");
  const deferredSearchText = useDeferredValue(searchText);
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["play", "cards"],
    queryFn: listPlayCards,
  });

  const cards = useMemo(() => {
    const normalizedKeyword = deferredSearchText.trim().toLowerCase();
    const allCards = data ?? [];
    if (!normalizedKeyword) {
      return allCards;
    }

    return allCards.filter((card) => {
      const haystack = [card.name, card.description ?? "", ...card.tags]
        .join(" ")
        .toLowerCase();
      return haystack.includes(normalizedKeyword);
    });
  }, [data, deferredSearchText]);

  const stats = useMemo(() => {
    const source = data ?? [];
    const withRecentSession = source.filter((card) => card.latest_session_id).length;
    const totalOpenings = source.reduce((sum, card) => sum + card.opening_count, 0);
    return {
      totalCards: source.length,
      withRecentSession,
      totalOpenings,
    };
  }, [data]);

  return (
    <div className="page-stack">
      <PageSection
        title="游玩模式首页"
        description="从这里浏览所有已发布角色卡，快速进入详情页，或直接恢复最近一次游玩会话。"
      >
        <div className="play-home-hero">
          <div className="play-home-hero__copy">
            <div className="pill-label">
              <Sparkles size={16} strokeWidth={1.8} />
              <span>角色卡驱动的沉浸入口</span>
            </div>
            <h3>先选角色，再进入会话。</h3>
            <p>
              当前首页已接入真实角色卡列表，后续会继续补搜索筛选增强、封面图、更多排序方式和推荐区块。
            </p>
          </div>
          <div className="metric-grid">
            <MetricCard label="已发布角色卡" value={stats.totalCards} />
            <MetricCard label="带最近会话角色" value={stats.withRecentSession} />
            <MetricCard label="可选开场总数" value={stats.totalOpenings} />
          </div>
        </div>

        <div className="play-toolbar">
          <label className="search-input">
            <Search size={18} strokeWidth={1.9} />
            <input
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="搜索角色名、描述或标签"
              aria-label="搜索角色卡"
            />
          </label>
          <div className="play-toolbar__meta">
            <span>共 {cards.length} 个结果</span>
          </div>
        </div>

        {isLoading ? (
          <div className="card-grid">
            {Array.from({ length: 6 }).map((_, index) => (
              <div className="play-card play-card--loading" key={index} />
            ))}
          </div>
        ) : null}

        {isError ? (
          <StatusCard
            title="角色卡列表加载失败"
            description={error instanceof Error ? error.message : "请检查后端服务是否已启动。"}
            tone="danger"
          />
        ) : null}

        {!isLoading && !isError && cards.length === 0 ? (
          <StatusCard
            title="暂无可显示的角色卡"
            description="当前没有已发布角色卡，或搜索条件没有命中结果。"
          />
        ) : null}

        {!isLoading && !isError && cards.length > 0 ? (
          <div className="card-grid">
            {cards.map((card) => (
              <PlayCardCard key={card.id} card={card} />
            ))}
          </div>
        ) : null}
      </PageSection>
    </div>
  );
}

function PlayCardCard({ card }: { card: PlayCardSummary }) {
  return (
    <article className="play-card">
      <div className="play-card__visual">
        <div className="play-card__avatar">
          {card.name.trim().slice(0, 1).toUpperCase()}
        </div>
        <div className="play-card__chips">
          <span className="soft-chip">
            <Compass size={14} strokeWidth={1.9} />
            {card.opening_count} 个开场
          </span>
          {card.latest_session_id ? (
            <span className="soft-chip">
              <MessageCircleMore size={14} strokeWidth={1.9} />
              可继续游玩
            </span>
          ) : null}
        </div>
      </div>

      <div className="play-card__body">
        <div className="play-card__head">
          <div>
            <h3>{card.name}</h3>
            <p>{card.description?.trim() || "当前角色卡暂无简介。进入详情页后可查看会话与开场。"}</p>
          </div>
        </div>

        <div className="tag-row">
          {card.tags.length > 0 ? (
            card.tags.slice(0, 4).map((tag) => (
              <span key={tag} className="tag-chip">
                {tag}
              </span>
            ))
          ) : (
            <span className="tag-chip tag-chip--muted">暂无标签</span>
          )}
        </div>

        <dl className="meta-list">
          <div>
            <dt>发布时间</dt>
            <dd>{formatDateTime(card.published_at)}</dd>
          </div>
          <div>
            <dt>最近会话</dt>
            <dd>{card.latest_session_id ? "可继续" : "尚未开始"}</dd>
          </div>
        </dl>
      </div>

      <div className="action-row">
        <Link className="button button--primary" to={`/play/${card.id}`}>
          查看详情
        </Link>
        {card.latest_session_id ? (
          <Link className="button button--ghost" to={`/play/session/${card.latest_session_id}`}>
            继续最近会话
          </Link>
        ) : null}
      </div>
    </article>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
