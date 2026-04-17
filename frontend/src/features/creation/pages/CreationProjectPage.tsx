import { useParams } from "react-router-dom";

import { FeatureList } from "../../../components/common/FeatureList";
import { InfoCard } from "../../../components/common/InfoCard";
import { PageSection } from "../../../components/common/PageSection";

export function CreationProjectPage() {
  const { projectId } = useParams();

  return (
    <div className="page-stack">
      <PageSection
        title="创作项目工作台"
        description={`当前为项目 ${projectId ?? "未指定"} 的工作台骨架，后续承接资产树、创作会话与世界书入口。`}
      >
        <div className="session-layout">
          <InfoCard eyebrow="工作台目标" title="核心区域">
            <FeatureList
              items={[
                "项目概览与基础信息",
                "角色卡 / 世界书 / 预设 / 素材资产入口",
                "创作会话工作区",
                "右侧预览与调试扩展区",
              ]}
            />
          </InfoCard>
          <InfoCard eyebrow="接口映射" title="优先联调">
            <FeatureList
              items={[
                "GET /v1/creation/projects/{project_id}",
                "PUT /v1/creation/projects/{project_id}",
                "GET /v1/creation/sessions/{session_id}/overview",
                "GET /v1/creation/sessions/{session_id}/traces/latest",
              ]}
            />
          </InfoCard>
        </div>
      </PageSection>
    </div>
  );
}
