# Izumi Studio — 可用模型列表

> 最后更新：2026-04-14
> 基于 .env 配置的 API Key 实际查询结果

---

## 1. Claude（onetoken 中转代理）

**配置：**
- `CLAUDE_API_URL` = `http://100.88.8.9/`
- `CLAUDE_API_KEY` = `sk-EkPj...`
- 接口格式：OpenAI 兼容

| 模型 ID | 系列 | 说明 | 视觉 |
|---------|------|------|------|
| `claude-sonnet-4-6` | Claude 4.6 | 当前最新 Sonnet，推荐主力 | ✓ |
| `claude-opus-4-6` | Claude 4.6 | 最强 Opus | ✓ |

**推荐用途：**
- 主力创作与游玩对话：`claude-sonnet-4-6`
- 最高质量输出：`claude-opus-4-6`

---

## 2. Qwen（阿里云 DashScope）

**配置：**
- `QWEN_API_URL` = `https://dashscope.aliyuncs.com/compatible-mode/v1`
- `QWEN_API_KEY` = `sk-df93...`
- 接口格式：OpenAI 兼容

### 2.1 通用对话模型

| 模型 ID | 上下文 | 说明 | 视觉 |
|---------|--------|------|------|
| `qwen-max-latest` | 32K | 旗舰，最强推理 | ✗ |
| `qwen-max-2025-01-25` | 32K | Qwen-Max 固定版 | ✗ |
| `qwen-plus-latest` | 131K | 均衡性能 | ✗ |
| `qwen-turbo-latest` | 1M | 最快/最便宜 | ✗ |
| `qwen-long` | 10M | 超长上下文 | ✗ |
| `qwq-plus` | 131K | 推理增强（类 o1） | ✗ |
| `qwq-plus-2025-03-05` | 131K | QwQ-Plus 固定版 | ✗ |
| `qwen3-max` | 131K | Qwen3 旗舰 | ✗ |
| `qwen3-max-2026-01-23` | 131K | Qwen3-Max 固定版 | ✗ |
| `qwen3-235b-a22b` | 131K | 最强开源 MoE | ✗ |
| `qwen3-32b` | 131K | Qwen3 开源 32B | ✗ |

### 2.2 视觉理解模型

| 模型 ID | 说明 |
|---------|------|
| `qwen-vl-max-latest` | 视觉旗舰，推荐 |
| `qwen-vl-plus-latest` | 视觉均衡 |
| `qwen2.5-vl-72b-instruct` | 开源视觉大模型 |
| `qwen3-vl-plus` | Qwen3 视觉版 |
| `qvq-max` | 视觉推理增强 |

### 2.3 图片生成模型

| 模型 ID | 说明 |
|---------|------|
| `qwen-image-2.0-pro` | 最新图片生成旗舰 |
| `qwen-image-2.0` | 标准图片生成 |
| `qwen-image-plus` | 图片生成均衡版 |
| `qwen-image-edit-plus` | 图片编辑（inpaint/修改） |
| `wan2.7-image-pro` | 万象视频/图片 Pro |
| `wan2.7-image` | 万象标准版 |

**推荐用途：**
- 快速/廉价对话：`qwen-turbo-latest`
- 长上下文处理：`qwen-long`（10M token）
- 视觉理解：`qwen-vl-max-latest`
- 图片生成：`qwen-image-2.0-pro`

---

## 3. DeepSeek

**配置：**
- `DEEPSEEK_API_URL` = `https://api.deepseek.com`
- `DEEPSEEK_API_KEY` = `sk-230d...`
- 接口格式：OpenAI 兼容

| 模型 ID | 上下文 | 说明 | 视觉 |
|---------|--------|------|------|
| `deepseek-chat` | 64K | 通用对话（DeepSeek-V3），性价比极高 | ✗ |
| `deepseek-reasoner` | 64K | 推理链（DeepSeek-R1），类 o1 | ✗ |

> 注意：DashScope 渠道也有 DeepSeek 模型（`deepseek-v3`、`deepseek-r1` 等），可作备用。

**推荐用途：**
- 成本敏感场景：`deepseek-chat`（价格极低）
- 复杂推理任务：`deepseek-reasoner`

---

## 4. Kimi（月之暗面）

**配置：**
- `KIMI_API_URL` = `https://api.moonshot.cn/v1`
- `KIMI_API_KEY` = `sk-oIlN...`
- 接口格式：OpenAI 兼容

| 模型 ID | 上下文 | 说明 | 视觉 |
|---------|--------|------|------|
| `kimi-k2.5` | 128K | 最新旗舰，综合最强 | ✗ |
| `kimi-k2-thinking` | 128K | K2 深度思考版 | ✗ |
| `kimi-k2-turbo-preview` | 128K | K2 快速版 | ✗ |
| `moonshot-v1-auto` | 自动 | 自动选择上下文窗口 | ✗ |
| `moonshot-v1-128k` | 128K | 128K 长上下文 | ✗ |
| `moonshot-v1-128k-vision-preview` | 128K | 128K 视觉理解 | ✓ |
| `moonshot-v1-32k` | 32K | 32K 标准版 | ✗ |
| `moonshot-v1-8k` | 8K | 8K 快速版 | ✗ |

**推荐用途：**
- 主力对话：`kimi-k2.5`
- 长文档/长对话：`moonshot-v1-128k`

---

## 5. Azure OpenAI

**配置：**
- `AZURE_OPENAI_ENDPOINT` = `https://longood-gpt4.openai.azure.com/`
- `AZURE_OPENAI_API_KEY` = `782e...`
- 接口格式：Azure OpenAI（需要 deployment name，不同于模型 ID）

> **重要：** Azure OpenAI 使用 deployment name 而非模型 ID 调用。以下为该账号可接入的**基础模型**，实际可用取决于 Azure Portal 中已创建的 deployment。

| 基础模型 | 说明 | 视觉 |
|---------|------|------|
| `gpt-4o-2024-11-20` | GPT-4o 最新稳定版 | ✓ |
| `gpt-4o-2024-08-06` | GPT-4o | ✓ |
| `gpt-4o-mini-2024-07-18` | GPT-4o Mini，快速廉价 | ✓ |
| `gpt-4-turbo-2024-04-09` | GPT-4 Turbo | ✓ |
| `dall-e-3-3.0` | DALL-E 3 图片生成 | — |

**推荐用途：**
- 通用对话：GPT-4o 系列（需确认 deployment 名称）
- 图片生成：DALL-E 3（需确认 deployment 名称）

---

## 6. Izumi Studio 模型配置建议

### 按用途推荐

| 用途 | 首选模型 | 备选模型 | 渠道 |
|------|---------|---------|------|
| 游玩模式主力 | `claude-sonnet-4-6` | `qwen-max-latest` | onetoken / DashScope |
| 创作模式生成 | `claude-sonnet-4-6` | `qwen-plus-latest` | onetoken / DashScope |
| 聊天模式日常 | `claude-sonnet-4-6` | `qwen-turbo-latest` | onetoken / DashScope |
| 摘要生成（后台） | `qwen-turbo-latest` | `deepseek-chat` | DashScope / DeepSeek |
| 推理/复杂任务 | `claude-opus-4-6` | `qwq-plus` | onetoken / DashScope |
| 视觉理解 | `claude-sonnet-4-6` | `qwen-vl-max-latest` | onetoken / DashScope |
| 图片生成 | `qwen-image-2.0-pro` | DALL-E 3 (Azure) | DashScope / Azure |
| 长上下文（>100K） | `qwen-long` | `moonshot-v1-128k` | DashScope / Kimi |

### 成本优先方案

摘要生成、关键词匹配、辅助任务建议使用 `deepseek-chat` 或 `qwen-turbo-latest`，价格极低，适合高频后台调用。

---

*此文档根据 API 实际查询生成，模型可用性以各供应商实时状态为准。*
