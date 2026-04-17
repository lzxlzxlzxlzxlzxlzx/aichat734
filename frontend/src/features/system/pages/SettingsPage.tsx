import { FeatureList } from "../../../components/common/FeatureList";
import { InfoCard } from "../../../components/common/InfoCard";
import { PageSection } from "../../../components/common/PageSection";

export function SettingsPage() {
  return (
    <div className="page-stack">
      <PageSection
        title="设置页骨架"
        description="这一页会在后续承接模型配置、预设管理、快速回复、人格与偏好设置。"
      >
        <div className="panel-grid">
          <InfoCard eyebrow="计划承接" title="设置模块">
            <FeatureList
              items={[
                "模型配置",
                "预设与破限常驻策略",
                "快速回复与人格",
                "界面偏好与开发调试开关",
              ]}
            />
          </InfoCard>
        </div>
      </PageSection>
    </div>
  );
}
