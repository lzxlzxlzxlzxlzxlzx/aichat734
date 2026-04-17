import { useParams } from "react-router-dom";

import { FeatureList } from "../../../components/common/FeatureList";
import { InfoCard } from "../../../components/common/InfoCard";
import { PageSection } from "../../../components/common/PageSection";

export function CreationCardPage() {
  const { cardId } = useParams();

  return (
    <div className="page-stack">
      <PageSection
        title="角色卡编辑页"
        description={`当前为角色卡 ${cardId ?? "未指定"} 的创作页骨架，后续承接基础字段、版本信息和创作联动入口。`}
      >
        <div className="panel-grid">
          <InfoCard eyebrow="编辑方向" title="页面内容">
            <FeatureList
              items={[
                "基础信息与描述字段",
                "预设、标签、版本信息",
                "快速保存与最近修改记录",
                "跳转游玩 / 进入创作会话",
              ]}
            />
          </InfoCard>
          <InfoCard eyebrow="接口映射" title="优先联调">
            <FeatureList
              items={[
                "GET /v1/creation/cards/{card_id}",
                "PUT /v1/creation/cards/{card_id}",
                "GET /v1/creation/cards/{card_id}/sessions",
                "POST /v1/creation/cards/{card_id}/sessions",
              ]}
            />
          </InfoCard>
        </div>
      </PageSection>
    </div>
  );
}
