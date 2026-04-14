# ReZero V2.2 角色卡解析文档

> 文件：`ReZero_V2.2.png`
> 格式：Character Card V3 (chara_card_v3 / spec_version 3.0)
> 作者：Seija
> 版本：v2.0.0
> 关联世界书：`REZero_BlackTea_v2.0.0`
> 来源讨论：https://discord.com/channels/1291925535324110879/1436606578353504347

---

## 一、卡片结构概述

该角色卡属于**叙事型世界扮演卡（IP 世界卡）**，而非单角色扮演卡。整个卡片不扮演某个具体角色，而是提供《Re:Zero》原作世界的完整知识库，让玩家可以从**任意章节**进入剧情，以 `<user>` 身份在原作世界中自由行动。

### 核心设计理念

| 维度 | 设计 |
|------|------|
| 角色定位 | 世界容器，非单一角色 |
| 玩法入口 | 输入 `<第X章>` 进入对应剧情节点 |
| 知识来源 | 全部以 WI 条目形式存储，按需激活 |
| 技术特色 | MVU 变量系统 + 章节动态解锁 + EJS 模板语法 |

---

## 二、顶层数据结构（ccv3 格式）

```
角色卡 (PNG tEXt chunk)
├── 顶层字段（v2 兼容层）
│   ├── name: "ReZero 从零开始的异世界生活"
│   ├── first_mes: 入场提示（无预设开场白，需用户输入章节）
│   ├── description / personality / scenario: 全部为空
│   └── spec: "chara_card_v3"
│
└── data（v3 核心）
    ├── creator: "Seija"
    ├── character_version: "v2.0.0"
    ├── system_prompt: ""（空，依赖 WI）
    ├── post_history_instructions: ""（空）
    ├── extensions
    │   ├── world: "REZero_BlackTea_v2.0.0"（关联外部世界书名称）
    │   ├── depth_prompt: { prompt:"", depth:4, role:"system" }
    │   ├── tavern_helper.scripts: [MVU-BETA 脚本]
    │   └── regex_scripts: [2 个 Regex 脚本]
    └── character_book（内嵌世界书，210 条目）
```

### 字段说明

- **`description/personality/scenario` 全空**：作者将所有设定信息转移到 WI 条目中管理，避免占用固定 token。
- **`extensions.world`**：指向外部独立世界书文件名，使用时需同时加载该世界书。
- **`depth_prompt`**：该卡的 Character Note 为空，深度注入功能未启用。

---

## 三、扩展系统：MVU-BETA 变量引擎

### 3.1 什么是 MVU

MVU（MagVarUpdate）是由 MagicalAstrogy 开发的 SillyTavern 扩展脚本，通过 `tavern_helper.scripts` 注入。

```json
{
  "name": "MVU-BETA",
  "content": "import 'https://testingcf.jsdelivr.net/gh/MagicalAstrogy/MagVarUpdate@beta/artifact/bundle.js'"
}
```

### 3.2 MVU 变量语法

WI 条目内容中使用 **EJS 模板语法**读写变量：

| 语法 | 作用 |
|------|------|
| `<%= getvar('stat_data.chapter') %>` | 读取变量，输出值 |
| `_.set('chapter', ${新值})` | 写入变量 |
| `<%_ if (getvar('stat_data.chapter') >= 82) { _%>...<%_ } _%>` | 条件渲染（章节解锁） |

### 3.3 核心变量

| 变量路径 | 用途 |
|----------|------|
| `stat_data.chapter` | 当前所在章节编号，控制状态栏显示和内容解锁 |

### 3.4 MVU 功能按钮

卡片注册了 6 个操作按钮（默认不可见，可通过 ST 界面显示）：

| 按钮 | 功能 |
|------|------|
| 重新处理变量 | 重新解析当前对话中的所有变量 |
| 重新读取初始变量 | 重置到初始变量状态 |
| 快照楼层 | 为当前消息层创建变量快照 |
| 重演楼层 | 回放某一楼层的变量状态 |
| 重试额外模型解析 | 用附加模型重新解析变量更新块 |
| 清除旧楼层变量 | 清理历史楼层的变量数据 |

---

## 四、Regex 脚本（2 个）

### 脚本 1：折叠变量更新块

| 字段 | 值 |
|------|----|
| 名称 | `[折叠]完整变量更新` |
| 查找正则 | `/<(update(?:variable)?)>\s*((?:(?!<\1>).)*)\s*<\/\1>/gsi` |
| 替换为 | `<details><summary>变量更新情况</summary>$2</details>` |
| 作用范围 | 显示时（placement: [1, 2]，markdownOnly: true） |

**效果**：将模型输出的 `<update>...</update>` 块折叠成可展开的 `<details>` 折叠组件，不干扰正文阅读。

### 脚本 2：清除变量/状态栏标签（发送前）

| 字段 | 值 |
|------|----|
| 名称 | `去除变量,去除状态栏标签` |
| 查找正则 | `/<update(?:variable)?>(?:(?!.*<\/update(?:variable)?>).*$|.*<\/update(?:variable)?>)|<\/?(?:font\|small\|br)\b[^>]*\/?>/gsi` |
| 替换为 | `""` |
| 作用范围 | 发送到模型前（promptOnly: true） |

**效果**：在将历史消息发送给 LLM 时，自动去除变量更新块和 HTML 标签（font/small/br），防止它们污染上下文，节省 token。

---

## 五、内嵌世界书（210 条目）

### 5.1 条目分类统计

| 类别 | 条目数 | 触发方式 | 位置 |
|------|--------|----------|------|
| ⚙️系统/设定（constant 永久激活） | ~15 | constant=true | before_char |
| 🐉地理/机构/国家 | ~10 | 关键词触发 | before_char |
| 🕊️爱蜜莉雅阵营人物 | ~13 | 关键词触发 | before_char |
| 🏃菲鲁特阵营人物 | ~5 | 关键词触发 | before_char |
| 💃普莉希拉阵营人物 | ~3 | 关键词触发 | before_char |
| 🎖️库珥修阵营人物 | ~3 | 关键词触发 | before_char |
| 🦊安娜阵营人物 | ~6 | 关键词触发 | before_char |
| 📓魔女教人物/组织 | ~8 | 关键词触发 | before_char |
| 🧹魔女人物 | ~6 | 关键词触发 | before_char |
| 🐋/🐇/🐍 三大魔兽 | 3 | 关键词触发 | before_char |
| 📜历史事件 | ~4 | 关键词触发 | before_char |
| **📖章节条目（第1~111章）** | **~111** | `第X章` 关键词触发 | after_char |
| 🔆状态栏/章节设定 | 2 | constant=true | after_char |

### 5.2 WI 条目标准字段

每个条目含以下关键字段：

```
id             - 唯一标识
comment        - 作者备注（不注入，仅显示在编辑界面）
keys           - 主关键词列表（触发条件）
secondary_keys - 次关键词（AND 逻辑辅助过滤）
content        - 注入内容（支持 EJS 模板）
constant       - true = 永久激活，忽略关键词
selective      - 选择性逻辑开关
enabled        - 是否启用
position       - before_char（角色定义前）/ after_char（聊天历史后）
insertion_order- 注入排序权重
extensions.depth         - 注入深度（距消息历史末尾的位置）
extensions.probability   - 激活概率（0-100）
extensions.sticky        - 激活后保持 N 轮
extensions.cooldown      - 冷却轮数
extensions.delay         - 延迟触发轮数
extensions.prevent_recursion - 防止被递归扫描再次激活
extensions.exclude_recursion - 排除递归扫描
extensions.selectiveLogic    - AND_ANY(0)/AND_ALL(1)/NOT_ANY(2)/NOT_ALL(3)
extensions.group             - 分组名
extensions.group_weight      - 分组权重（组内竞争）
extensions.vectorized        - 向量化检索
```

### 5.3 永久激活条目（constant=true）

这些条目不需要关键词，每轮对话都注入：

| 条目 | 内容 | position | order |
|------|------|----------|-------|
| `⚙️基础&世界设定` | 地理/四大国/魔法体系/历史 | before_char | 5 |
| `⚙️时间&历法设定` | 月份/季节/时刻/纪年方式 | before_char | 6 |
| `⚙️货币&收入设定` | 货币体系/物价/收入参考 | before_char | 7 |
| `⚙️饮食&习惯设定` | 食材/饮品/饮食文化 | before_char | 8 |
| `⚙️权能&加护设定` | 七大罪权能/加护概念 | before_char | 11 |
| `⚙️诅咒&解咒设定` | 诅咒机制 | before_char | 10 |
| `⚙️种族占位` | 种族基础信息 | before_char | 13/15 |
| `露格尼卡亲龙王国` | 王国详细设定 | before_char | 20 |
| `⚙️全局要求` | 全局 GM 规则 | before_char | 4 |
| `🔆状态栏` | 状态栏格式定义 | after_char | 1 |
| `🔆章节设定(自动切章节)` | 章节切换逻辑 | after_char | 700 |
| `变量提示词` | 变量更新规则（`chapter` 变量） | after_char | 5 |
| `[initvar]` | 初始化变量默认值 | before_char | 100 |

### 5.4 章节条目设计（核心机制）

**触发方式**：用户输入 `<第X章>` → 关键词 `第X章` 匹配 → 对应章节条目激活

**章节范围**：第1章（第一卷）～ 第111章（第二十卷），共 ~111 条

**注入位置**：`after_char`，order=701，depth 值分两段：
- 第 1-29 章：depth=3（较深注入，提供更多上下文）
- 第 30 章起：depth=1（浅注入，仅在最近 1 条消息处插入，节省 token）

**章节内容结构**（以第5章为例，4806字）：
```
- 时间线节点
- 各角色在该章节的状态/位置/目标
- 关键事件摘要
- 昴当前能力/记忆/限制
- 已知剧情和待解谜题
```

**条件解锁内容**（EJS 语法）：
```ejs
<%_ if (getvar('stat_data.chapter') >= 82) { _%>
- 卡佩拉相关内容（82章后才解锁，避免剧透）
<%_ } _%>
```

### 5.5 人物条目设计

以核心人物为例，条目内容长度：

| 人物 | 关键词 | 内容长度 |
|------|--------|----------|
| 菜月昴 | 菜月昴/昴/斯巴鲁 | 8368 字 |
| 碧翠丝 | 贝蒂/碧翠丝/贝阿特丽丝 | 9778 字 |
| 加菲尔 | 加菲尔/加菲/汀泽尔 | 8360 字 |
| 罗兹瓦尔 | 罗兹瓦尔/梅扎斯 | 7195 字 |
| 莱因哈鲁特 | 莱因哈鲁特/剑圣 | 7891 字 |
| 爱蜜莉雅 | 爱蜜莉雅/艾米莉亚/半魔 | 6649 字 |

人物条目包含：背景/种族/性别/年龄/外貌/身份/性格/能力/关系/要点 等结构化字段。

---

## 六、状态栏系统

条目 `[215] 🔆状态栏` (constant=true, after_char, order=1) 定义了状态栏格式：

```
content 长度：699 字
位置：after_char（插入在聊天历史之后）
插入顺序：1（最优先）
```

状态栏通过 MVU 变量系统读取 `stat_data.chapter` 等变量，在每条模型回复后动态显示当前章节/状态信息。

---

## 七、章节自动切换机制

条目 `[217] 🔆章节设定(自动切章节)` (constant=true, after_char, order=700) 定义了自动章节切换规则：

```
规则：模型在回复末尾输出 <update>_.set('chapter', 新值);</update> 时，
MVU 脚本解析该块并更新 stat_data.chapter 变量，
触发对应章节的 WI 条目激活/停用。
```

**工作流程**：
```
用户输入 "<第5章>" 
→ WI 关键词匹配激活 [98]第5章条目
→ 模型读取章节设定，开始扮演
→ 模型回复末尾输出 <update>_.set('chapter', 5);</update>
→ MVU 解析并写入 stat_data.chapter = 5
→ 后续轮次根据章节变量值解锁/锁定条目内容
```

---

## 八、设计亮点总结

### 1. IP 知识与剧情分离

- **设定层**（constant 永久激活）：世界基础、魔法体系、货币、饮食等背景知识，始终在上下文中
- **剧情层**（关键词触发）：章节事件、人物状态，仅在玩家进入对应章节时激活

### 2. 渐进式剧透控制

通过 EJS 条件语法 `if (chapter >= N)` 实现章节锁：角色档案中涉及剧情的敏感内容只在用户已经进入对应章节后才显示。

### 3. Token 效率优化

| 策略 | 实现 |
|------|------|
| description/personality/scenario 全空 | 避免固定字段占用 token |
| 早期章节 depth=3，后期章节 depth=1 | 控制早期章节的上下文厚度 |
| Regex 清除状态栏 HTML 标签（发送前） | 防止标签污染 LLM 上下文 |
| Regex 折叠变量更新块（显示时） | 保持界面整洁，不影响 token |
| 魔法/权能等设定以 keyword 触发 | 仅在相关剧情中注入，不常驻 |

### 4. 无固定开场白设计

`first_mes` 只说明"请输入 `<第X章>`"，让玩家主动选择入场点，支持跳章扮演，这是传统线性角色卡不具备的能力。

---

## 九、技术规格汇总

| 项目 | 值 |
|------|----|
| 格式 | Character Card V3 (chara_card_v3) |
| WI 条目数 | 210 |
| 永久激活条目 | ~15 |
| 关键词触发条目 | ~195 |
| 章节覆盖范围 | 第 1-111 章（轻小说第 1-20 卷） |
| 最大单条目内容 | ~9778 字（碧翠丝） |
| 变量引擎 | MVU-BETA (EJS 模板) |
| Regex 脚本数 | 2 |
| 状态栏 | 有（`stat_data.chapter` 驱动） |
| 关联外部世界书 | REZero_BlackTea_v2.0.0 |
