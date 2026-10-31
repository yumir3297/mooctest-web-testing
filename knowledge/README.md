# 赛前知识库导航（Web 应用测试赛道）— ARCHIVE / 非规范

> ## ⚠ ARCHIVE / 非规范（v1.0，2026-10-31 归档）
>
> 本目录是**历史知识库**，保留用于来源追溯与历史对照，**不再作为运行时规范来源**。
> 其中的 `08_derived_rules/` 三份自编规则已被 v0.2.1 规则体系取代，部分条目（每边界四点、`TC-WEB-xxx` 命名）**已作废**。
>
> **运行时规范源**（按优先级）：
>
> 1. 规则正文：`.opencode/skills/test-design-methodology/`（`SKILL.md` + `references/`）
> 2. 规则台账：`mooctest-knowledge/inventory/rule_registry.csv`（rule_id / 版本 / 权威来源 / 弃用映射）
> 3. 命名与证据约定：`docs/CONVENTIONS.md`
> 4. 工作流：`docs/WORKFLOW.md`
>
> 本文件以下内容均为 **v1.0 历史记录**，不得据此设计用例或组织提交物。

## 什么时候读哪个文件（运行时重定向）

| 当前任务 | 读这个（规范） | 不要读（归档/作废） |
|---|---|---|
| 拿到赛题/需求，准备设计用例 | `.opencode/skills/test-design-methodology/SKILL.md` → `references/method_selector.md` | `08_derived_rules/test_design_decision_rules.md`（方法矩阵与四点边界作废） |
| 需要确认比赛交付物与评分维度 | `knowledge/01_competition_official/P0-03_*_text.txt`（2025 基线）+ `P0-01_*_text.txt`（2026 交付物） | — |
| 要写/改 Selenium 脚本 | `docs/WORKFLOW.md` §3 + `.opencode/skills/selenium-testing/`；版本实时值以 `python tools/env_check.py` 为准 | `08_derived_rules/selenium_agent_rules.md` 的版本表（Chrome 155/Driver 155 已过时） |
| 要探索页面结构 | `.opencode/skills/browser-exploration/` + `knowledge/03_selenium_pytest/00_index.md` | 不要镜像整站 |
| 要组织提交物（Excel/代码/截图） | `docs/CONVENTIONS.md` | `08_derived_rules/submission_schema.md`（`TC-WEB-xxx`/`SHOT-...`/`RUN-YYYYMMDD-01` 作废） |
| 需要方法论出处 | `references/sources_index.md`（Skill 内置）+ `knowledge/02_istqb/` 按章节检索 | 不要整本粘贴 |
| 需要课程/视频入口 | `knowledge/06_mooctest_courses/README.md` | — |

---

## 历史记录：v1.0 原「什么时候读哪个文件」

> 下表为归档原文，仅用于对照当时的设计意图；其中指向 `08_derived_rules/` 的入口一律不再有效。

| 当前任务 | 读这个 | 不要读 |
|---|---|---|
| 拿到赛题/需求，准备设计用例 | `08_derived_rules/test_design_decision_rules.md` | 不要读 datasheet 原文 |
| 需要确认比赛交付物与评分维度 | `01_competition_official/P0-03_*_text.txt`（2025 基线）+ `P0-01_*_text.txt`（2026 交付物） | — |
| 要写/改 Selenium 脚本 | `08_derived_rules/selenium_agent_rules.md` | 不要读 ISTQB 大纲 |
| 要探索页面结构 | `03_selenium_pytest/00_index.md` → 需要时查 llms.txt | 不要镜像整站 |
| 要组织提交物（Excel/代码/截图） | `08_derived_rules/submission_schema.md` | — |
| 需要方法论出处 | `02_istqb/P0-04_..._text.txt`（按章节检索） | 不要整本粘贴 |
| 需要课程/视频入口 | `06_mooctest_courses/README.md` | — |

## 目录结构（历史记录）

```
knowledge/
  00_source_registry.csv          # 16+ 条资源登记（含 SHA-256、许可、状态）
  01_competition_official/        # 2026 报名/复赛通知 + 2025 Web 赛项说明（评分基线）
  02_istqb/                       # ISTQB CTFL v4.0.1 官方大纲 + 认证页
  03_selenium_pytest/             # Selenium/pytest 单页文档 + llms.txt + 本地索引
  04_iso_public_summaries/        # ISO 标准：仅公开摘要与链接（正文付费，未获取）
  05_books_bibliography/          # 三本教材书目与合法获取入口（无正文）
  06_mooctest_courses/            # 慕测公开课程大纲 + 待登录/待观看项
  07_skill_source_notes/          # 已装 Skills 的能力边界（不重复建设）
  08_derived_rules/               # 三份原创判定规则（本库核心产出）
  DOWNLOAD_REPORT.md              # 获取与验证报告
```

## 优先级与冲突（历史记录，已被取代）

> 以下排序反映 v1.0 的判断，其中第 4 条「本库 `08_derived_rules/` 的判定规则」**已失效**；
> 现行优先级以 `.opencode/skills/test-design-methodology/` + `mooctest-knowledge/inventory/rule_registry.csv` 为准。

1. 2026 赛题与当届评分细则（尚未发布的部分：NEEDS_USER_ACTION）
2. 2026 官方通知（`P0-01`、`P0-02`）
3. 2025 赛项说明与评分准则（**历史基线**，不可当作 2026 强制规则）
4. ~~本库 `08_derived_rules/` 的判定规则~~（已归档）
5. ISTQB / ISO / 教材（方法论来源）

## 事实与推断分离（历史记录）

- `01`–`07` 目录中是**抓取或登记的原始材料**，可直接引用。
- `08_derived_rules/` 是**本库自编的规则**，每条都标注了依据编号，属于「可执行的判断」，不是官方原文。
- 2026 官方评分细则尚未获取，AI 辅助工具许可尚未确认；任何关于“官方要求”的表述都必须标注为推断。
