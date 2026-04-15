# SillyTavern 代码分析 V1

## 1. 本轮分析目标

本轮只做第一步代码分析，聚焦于与你当前需求最相关的主链路：

- 用户输入是如何进入系统的
- 实际发送给模型的消息是在哪里拼装的
- 模型返回结果是在哪里接收的
- 哪些位置最适合加入“消息检查器 / Prompt Inspector”

当前不做实现修改，只做结构确认和后续切入点定位。

---

## 2. 当前结论摘要

`SillyTavern` 的聊天主链路可以概括为：

1. 用户在前端输入框输入内容
2. 前端入口函数 `sendTextareaMessage()` 触发发送
3. 发送核心函数 `Generate()` 开始组织上下文、角色、世界书、扩展注入和请求数据
4. 如果使用 Chat Completions 路线，则进入 `prepareOpenAIMessages()`
5. 前端通过 `sendOpenAIRequest()` 把 `generate_data` 发给本地后端
6. 本地后端 `/api/backends/chat-completions/generate` 再进行一次 provider 侧处理
7. 后端把最终 `requestBody` 发给真正的模型服务

这意味着如果你想满足“能清楚看到我的输入、实际发送消息和模型返回”的需求，至少要看两层：

- 前端层：你发送给 `SillyTavern` 后端的 payload
- 后端层：`SillyTavern` 最终发给模型厂商 API 的 payload

---

## 3. 发送入口主链路

### 3.1 用户输入入口

目前已确认：

- 输入框 DOM 是 `#send_textarea`
- 发送动作入口是 `sendTextareaMessage()`

关键代码位置：

- `public/index.html`
- `public/script.js`

其中 `sendTextareaMessage()` 的作用是：

- 读取输入框内容
- 判断是否是“空输入继续生成”
- 检查当前状态是否允许发送
- 最终调用 `Generate(generateType)`

这意味着，所有普通对话请求的统一入口基本都汇总到了 `Generate()`

---

## 4. 生成核心链路

### 4.1 `Generate()` 是最关键的中心函数

在 `public/script.js` 中，`Generate()` 是最重要的生成调度入口。

这一层会负责：

- 处理斜杠命令
- 判断生成类型
- 组织聊天上下文
- 注入世界书、角色信息、扩展提示
- 生成 `generate_data`
- 触发后续请求发送

已经确认的关键点：

- `Generate()` 在进入正式组装前会先执行 `processCommands(...)`
- 当数据准备完成后，会触发 `event_types.GENERATE_AFTER_DATA`

这个事件非常重要，因为它意味着：

- 请求数据已经准备好了
- 但此时还没有真正发出请求
- 是前端插入“查看本次请求内容”的理想位置之一

---

## 5. OpenAI / Chat Completions 路线

### 5.1 `prepareOpenAIMessages()` 负责拼装消息数组

在 `public/scripts/openai.js` 中，`prepareOpenAIMessages()` 是 Chat Completions 路线的核心组装函数。

这一层会处理：

- `scenario`
- `charDescription`
- `charPersonality`
- `worldInfoBefore`
- `worldInfoAfter`
- `extensionPrompts`
- `messages`
- `messageExamples`

从命名和结构上看，这一层已经非常接近你想看到的“实际发送给模型前的消息数组”。

也就是说，如果以后要做“透明查看器”，这里非常适合展示：

- 角色设定是如何进入上下文的
- 世界观是如何进入上下文的
- 历史消息是如何插入的
- 示例对话和额外扩展提示是如何参与拼装的

### 5.2 `sendOpenAIRequest()` 负责真正发给后端

`public/scripts/openai.js` 中的 `sendOpenAIRequest()` 会：

- 调用 `createGenerationParameters(...)`
- 得到 `generate_data`
- 触发 `event_types.CHAT_COMPLETION_SETTINGS_READY`
- 对 `/api/backends/chat-completions/generate` 执行 `fetch`

这说明前端最适合插入“查看实际发送 payload”的位置之一是：

- `createGenerationParameters(...)` 之后
- `fetch(...)` 之前

此时看到的是：

- 前端真正发给 `SillyTavern` 后端的完整 body

---

## 6. 后端路线

### 6.1 本地后端统一入口

在 `src/endpoints/backends/chat-completions.js` 中，统一入口是：

- `router.post('/generate', ...)`

这一层会先读取：

- `request.body.messages`
- `request.body.chat_completion_source`
- 自定义的 prompt 后处理配置

然后执行：

- `postProcessPrompt(...)`
- 根据不同 provider 分发到不同的 `send*Request(...)`

### 6.2 这里才是最接近“最终上游模型请求”的位置

前端发给后端的 payload 还不一定是最终形态。

后端还可能继续做：

- provider 格式转换
- 自定义 prompt 后处理
- 特定模型字段替换
- 多媒体嵌入
- system / user / tool 等消息格式调整

因此如果你要看“模型厂商最终实际收到的请求”，最准确的位置其实在：

- 各个 `send*Request(...)` 内部
- `fetch(...)` 发往上游 API 之前的 `requestBody`

这点非常关键，因为它决定了以后“消息检查器”最好分成两个视图：

- `前端请求视图`
- `最终上游请求视图`

---

## 7. 与你的需求最相关的切入点

### 7.1 需求一：看清输入、实际发送、模型返回

当前最合适的插入点如下：

#### 前端侧

- `public/script.js` 中的 `Generate()`
- `public/script.js` 中的 `event_types.GENERATE_AFTER_DATA`
- `public/scripts/openai.js` 中的 `prepareOpenAIMessages()`
- `public/scripts/openai.js` 中的 `sendOpenAIRequest()`
- `public/scripts/openai.js` 中的 `event_types.CHAT_COMPLETION_SETTINGS_READY`

#### 后端侧

- `src/endpoints/backends/chat-completions.js` 中的 `router.post('/generate', ...)`
- 各个 provider 的 `send*Request(...)`

#### 返回结果侧

当前已确认 `sendOpenAIRequest()` 里也负责：

- 处理 streaming response
- 处理非流式 response

这意味着未来不仅能展示：

- 原始请求
- 最终上游请求

也能展示：

- 原始流式返回片段
- 聚合后的模型回复

### 7.2 需求二：长期记忆

本轮还没有深入完整记忆实现，但已经确认：

- `Generate()` 和 `prepareOpenAIMessages()` 是上下文预算和消息组装的关键点
- 世界书、角色、历史消息在这一层进入最终上下文

因此以后要做长期记忆，核心不是简单“新增一个记忆文件”，而是要解决：

- 记忆如何存储
- 记忆如何在生成时召回
- 记忆如何参与 `prepareOpenAIMessages()` 的拼装

也就是说，记忆系统未来大概率会切入：

- 前端的上下文组装层
- 也可能需要增加新的持久化层和召回逻辑

### 7.3 需求三：多模态输入输出

本轮主分析对象是聊天主链路，但已有迹象说明：

- 不同 provider 分支会处理不同类型的返回内容
- `openai.js` 的流式处理里已经有图片相关分支

这说明 `SillyTavern` 本身已经不是纯文本架构，后续做图片与文件能力并不是完全从零开始。

### 7.4 需求四：世界观与角色系统

本轮确认了世界观和角色不是在最后一步临时拼上的，而是已经深度参与消息组装。

尤其是：

- `charDescription`
- `charPersonality`
- `scenario`
- `worldInfoBefore`
- `worldInfoAfter`

这些字段已经说明 `SillyTavern` 现有架构天然适合做角色和世界观增强。

这对你是个好消息，因为这意味着后续可以：

- 在现有系统上增强
- 而不是完全另起炉灶

---

## 8. 最值得继续深挖的文件

建议后续按下面顺序继续看：

1. `SillyTavern/public/script.js`
   - 重点：`sendTextareaMessage()`、`Generate()`

2. `SillyTavern/public/scripts/openai.js`
   - 重点：`prepareOpenAIMessages()`、`createGenerationParameters()`、`sendOpenAIRequest()`

3. `SillyTavern/public/scripts/PromptManager.js`
   - 重点：Prompt 排序和注入逻辑

4. `SillyTavern/public/scripts/world-info.js`
   - 重点：世界书如何被激活和插入

5. `SillyTavern/public/scripts/itemized-prompts.js`
   - 重点：是否已有接近“消息检查器”的现成基础

6. `SillyTavern/src/endpoints/backends/chat-completions.js`
   - 重点：最终发给模型厂商的请求结构

---

## 9. 第一阶段开发建议

结合本轮分析，如果你的第一目标是“看清我发了什么、系统实际发了什么、模型回了什么”，那么最合理的第一阶段不是直接改记忆，而是先做：

### 第一阶段建议功能

- 对话级 `Prompt Inspector`
- 显示用户原始输入
- 显示前端组装后的消息数组
- 显示前端发给本地后端的 `generate_data`
- 显示后端最终发给模型厂商的请求体
- 显示模型返回的原始数据和最终展示文本

### 为什么先做它

因为后面无论是：

- 长期记忆
- 世界观注入
- 角色人格稳定
- 图片理解与生成

都需要这个能力来判断“系统到底有没有按预期工作”。

---

## 10. 当前阶段结论

目前可以确认：

- `SillyTavern` 的主链路清晰，适合继续定制
- 你的第一个需求“消息透明化”是可做的，而且有很好的切入点
- 现有架构已经具备角色、世界观、上下文拼装的基础能力
- 后续最值得先做的是把前后端请求链路可视化

---

## 11. 下一步建议

下一步建议直接进入更细的一轮分析，聚焦其中一个方向：

### 方向 A：消息检查器

目标：

- 精确找出前端和后端应该挂在哪里
- 设计 UI 入口和数据结构

### 方向 B：记忆系统

目标：

- 找出现有摘要、上下文裁剪、世界书系统能复用多少
- 判断长期记忆应加在哪一层

### 方向 C：角色与世界观系统

目标：

- 找出现有角色卡和世界书的数据结构
- 判断怎样扩展成“更强的个人设定中心”

当前建议优先做 `方向 A：消息检查器`。

