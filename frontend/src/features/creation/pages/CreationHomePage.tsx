import { FeatureList } from "../../../components/common/FeatureList";
import { InfoCard } from "../../../components/common/InfoCard";
import { PageSection } from "../../../components/common/PageSection";

export function CreationHomePage() {
  return (
    <div className="page-stack">
      <PageSection
        title="创作模式首页"
        description="这里会承接项目、角色卡、最近编辑记录与后续的工作台入口。"
      >
        <div className="hero-grid">
          <InfoCard eyebrow="首页内容" title="核心区块">
            <FeatureList
              items={[
                "项目总览与最近项目",
                "角色卡资产区",
                "最近编辑记录",
                "新建角色卡 / 新建项目入口",
              ]}
            />
          </InfoCard>
          <InfoCard eyebrow="接口映射" title="优先联调">
            <FeatureList
              items={[
                "GET /v1/creation/home",
                "GET /v1/creation/projects",
                "GET /v1/creation/cards",
                "POST /v1/creation/projects 与 /cards",
              ]}
            />
          </InfoCard>
        </div>
      </PageSection>
    </div>
  );
}
