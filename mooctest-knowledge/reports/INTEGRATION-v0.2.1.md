# 知识库与 Skill 集成报告 v0.2.1（2026-10-31）

## 1. 结论摘要

- `test-design-methodology` 已从草案目录安装到运行时路径 `.opencode/skills/test-design-methodology/`，并通过 `debug skill` 出现在可加载列表中。
- 新增确定性阶段路由器 `tools/knowledge_router.py`：11 个阶段，启动即校验 Skill、知识文件与规则编号，缺失时非零退出（已做负向验证，退出码 1）。
- 三处规范冲突已消解：规范入口、BVA 覆盖口径、ID/证据命名。旧文件全部保留，仅加状态横幅，未删除正文。
- 2026 官方评分细则与 AI 使用许可**仍未确认**；本报告不把任何推断写成官方规则。

## 2. 权威源映射（主题 → 唯一规范文件 → 旧路径 → 状态）

| 主题 | 唯一规范文件 | 旧路径 | 状态 |
|---|---|---|---|
| 需求分诊、方法选择、分区与边界、判定表、状态迁移、组合覆盖、停止条件 | `.opencode/skills/test-design-methodology/references/method_selector.md` | `knowledge/08_derived_rules/test_design_decision_rules.md` | 旧文件 `archived`（仅历史对照） |
| 预期判据、失败归因、统计口径 | `.opencode/skills/test-design-methodology/references/test_oracle.md` | v0.2 新建，无旧文件 | `active` |
| 覆盖审查、去重、可判定性 | `.opencode/skills/test-design-methodology/references/coverage_review.md` | v0.2 新建，无旧文件 | `active` |
| 缺陷发现清单 | `.opencode/skills/test-design-methodology/references/defect_discovery.md` | v0.2 新建，无旧文件 | `active` |
| 来源与页码锚点 | `.opencode/skills/test-design-methodology/references/sources_index.md` | `knowledge/02_istqb/`、`knowledge/05_books_bibliography/` | 原始材料保留，不作为规则 |
| 规则编号与弃用映射 | `mooctest-knowledge/inventory/rule_registry.csv` | — | `active`（40 条 active） |
| ID、文件命名、证据布局 | `docs/CONVENTIONS.md` | `knowledge/08_derived_rules/submission_schema.md` | 旧文件 `archived` |
| 工作流与阶段产物 | `docs/WORKFLOW.md` | — | `active` |
| Selenium 编码与执行 | `.opencode/skills/selenium-testing/` + `docs/WORKFLOW.md` §3 | `knowledge/08_derived_rules/selenium_agent_rules.md` | `partial`（有效条款保留，版本表过时） |
| 阶段 → 知识路由 | `tools/knowledge_router.py` | — | `active`（新增） |

## 3. 已消解的冲突

### 冲突 1：规范入口自相矛盾

- **表现**：`knowledge/README.md` 把 `08_derived_rules/test_design_decision_rules.md` 列为设计入口；`mooctest-knowledge/decision-rules/README.md` 已把该文件标为 archive。
- **处置**：`knowledge/README.md` 顶部改为 `ARCHIVE / 非规范` 横幅，新增"运行时重定向"表；`decision-rules/README.md` 的规范路径改指已安装 Skill；`tools/knowledge_router.py` 在设计阶段把该旧文件列入 `avoid`。
- **现状**：设计阶段的唯一入口是 `.opencode/skills/test-design-methodology/`，旧文件仅作历史记录。

### 冲突 2：BVA 覆盖口径（四点 vs 2/3-value）

- **旧规则**：`test_design_decision_rules.md` §1、§5 要求每个边界取 `min-1 / min / max / max+1` 四点。
- **新规则**：`MS-01` 按 2-value（边界 + 相邻分区最近值）或 3-value（边界 + 两侧最近值）产生 2 或 3 个覆盖项，并明确"不得把每边界 4 点当成通用门禁"；精度必须与字段一致。
- **处置**：旧文件顶部横幅逐条列出作废条目与取代位置；`rule_registry.csv` 中 `MS-01-v0.1`、`REV-02-v0.1` 为 `deprecated`；路由器在设计阶段返回 `MS-01`。
- **影响**：`RUNTIME_CALL_TEST-20261031.md` 的 B 组按 3-value 生成 12 个边界覆盖项，而不是机械的 16 点。

### 冲突 3：ID 与截图命名

- **旧规则**：`submission_schema.md` 用 `TC-WEB-xxx` / `RUN-YYYYMMDD-01` / `SHOT-TC-WEB-xxx-01-PASS.png`。
- **新规则**：`docs/CONVENTIONS.md` 用 `TC-<模块>-<三位序号>` / `RUN-YYYYMMDD-HHMMSS` / `<case_id>__<stage>__<kind>__<UTC>.<ext>`。
- **处置**：旧文件横幅声明 §1、§5 命名作废并指向 `docs/CONVENTIONS.md`；§6「10 条自动校验」标注为"未实现（历史设想）"；路由器的 `case-review`、`packaging`、`quality-gate` 阶段把旧文件列入 `avoid`。
- **依据**：实际代码、`evidence/manifest.json` 与 `tools/evidence.py` 全部使用 `docs/CONVENTIONS.md` 的格式（主 Agent 已核实）。

### 附带修正：Selenium 版本表

`selenium_agent_rules.md` §1 的 Chrome 155 / Driver 155 / Selenium 4.51.0 / Python 3.13.9 / pytest 9.1.1 是写入时快照。已加 `PARTIAL` 横幅，声明实时值以 `python tools/env_check.py` 为准；其余条款（定位优先级、显式等待、断言、失败分类）保留有效。

## 4. 规则台账与 Skill 的关系

```
mooctest-knowledge/inventory/rule_registry.csv    # 台账：rule_id / 版本 / 权威来源 / 弃用映射
        │  canonical_file 指向
        ▼
.opencode/skills/test-design-methodology/references/*.md   # 规则正文（运行时加载）
        ▲
        │ SKILL.md 按需加载（不整目录通读）
tools/knowledge_router.py                          # 按阶段返回最小集合 + 校验引用
```

- 台账是**编号与状态**的唯一来源；Skill 是**规则正文**的唯一来源。二者不重复维护同一段文字。
- `scripts/check_refs.py` 会读取台账，校验 40 条 `active` 规则的 `canonical_file` 是否存在（全部通过）。
- 规则编号只增不重排；`MS-01-v0.1`、`MS-03-v0.1`、`MS-05-v0.1`、`MS-09-v0.1`、`REV-01-v0.1`、`REV-02-v0.1`、`ORA-04-v0.1` 保留为 `deprecated`。
- `LEGACY-01` 指向旧速查表，状态 `archived`，禁止与新规则同时编辑。

## 5. 2026 官方规则的边界声明

- **未获取**：2026 全国大学生软件测试大赛 Web 赛道的官方评分细则与权重。
- **未确认**：当届赛项对 AI 辅助工具的许可范围。
- 因此：
  - `method_selector.md` §3.4 的"Web 赛道默认优先级"明确标注为**推断**，不是官方规则；
  - 本报告与 Skill 中的任何"优先级""评分维度"表述，均来自 2025 赛项说明（历史基线）或工程经验，不得当作 2026 官方要求；
  - 提交前必须由人核对当届赛项文件；`docs/WORKFLOW.md` §9 已保留同一约束。

## 6. 验证命令与真实输出

### 6.1 Skill 依赖自检

```powershell
cd .opencode\skills\test-design-methodology
python scripts/check_refs.py
```

真实输出（退出码 0）：

```text
[OK]   SKILL.md version = 0.2.1
[OK]   references/method_selector.md (14500 bytes)
[OK]   references/test_oracle.md (7660 bytes)
[OK]   references/coverage_review.md (6838 bytes)
[OK]   references/defect_discovery.md (5120 bytes)
[OK]   references/sources_index.md (2432 bytes)
[OK]   rule_registry.csv 解析完成，active 规则 40 条

结果: 通过（errors=0, warnings=0）
```

### 6.2 运行时发现

```powershell
npx -y opencode-ai@1.19.3 debug skill
```

在该命令输出的 Skill 数组中检索 `test-design-methodology`，真实字段：

```text
name = test-design-methodology
location = <PROJECT_ROOT>\.opencode\skills\test-design-methodology\SKILL.md
description = 面向 Web 功能测试的需求分析与测试设计方法论：先做需求分诊，再按等价类、边界值（2-value/3-value）、判定表、状态迁移、组合覆盖选择方法与覆盖项，用 SPEC/DERIVED/PARTIAL/UNKNOWN 四档 oracle 定义可判定预期，最后按覆盖项做用例审查与 coverage 核对。适用于需求不完整、需要可判定且可追溯用例集的场景；不负责 Selenium 编码、脚本执行、截图取证与最终文档排版。
```

结论：Skill 已被 OpenCode 运行时发现，`name` 与目录名一致。

### 6.3 阶段路由

```powershell
python tools/knowledge_router.py --list-stages
```

真实输出（11 行，退出码 0）：

```text
requirement-analysis	只做需求分诊与可测性判定，不产出用例与脚本。
test-design	按 MS-00→方法选择→覆盖项→ORA 判据产出用例，不写 Selenium 代码。
case-review	按覆盖项与判据审查，不以用例条数作为通过标准。
browser-exploration	探索只确认真实 DOM 与交互路径，结论取证后才回写用例。
script-generation	以显式等待与稳定定位实现既有用例，不新增需求外断言。
execution	只执行已设计用例并落证据，未跑不得写 PASS。
failure-triage	先归因脚本/环境/业务/规格，再决定修脚本或登记缺陷。
visual-evidence	像素差异只是复核信号，不单独定性为缺陷。
reporting	报告只汇总已执行且有证据的结论，缺口单列。
packaging	按 docs/CONVENTIONS.md 的 ID 与文件布局打包，旧 TC-WEB/SHOT 命名不采用。
quality-gate	以覆盖项、证据可追溯与未执行状态为门禁项，任一不满足即不通过。
```

5 个代表性阶段的 JSON 摘要：

| 阶段 | skills | knowledge（数量） | rules（数量） | avoid |
|---|---|---|---:|---:|---|
| requirement-analysis | test-design-methodology, test-case-design | 2 | 3 | 1 |
| test-design | test-design-methodology, test-case-design | 3 | 12 | 2 |
| case-review | test-design-methodology | 2 | 9 | 1 |
| execution | selenium-testing | 2 | 3 | 0 |
| quality-gate | mooctest-web-testing | 3 | 7 | 1 |

完整 JSON 由命令直接输出，未在此展开；各阶段集合互不相同，未出现"每阶段返回全部文件"。

### 6.4 缺失引用负向测试

在内存中给 `test-design` 追加一个不存在的知识路径（不修改仓库文件），再调用同一入口：

```powershell
python -c "import sys; sys.path.insert(0,'tools'); import knowledge_router as r; r.STAGES['test-design']['knowledge'].append('.opencode/skills/test-design-methodology/references/does-not-exist.md'); sys.exit(r.main(['--stage','test-design']))"
```

真实输出与退出码：

```text
[FAIL] test-design: knowledge 路径不存在 -> .opencode/skills/test-design-methodology/references/does-not-exist.md

路由校验未通过：缺失或不一致 1 项
EXIT=1
```

另测非法阶段名：`python tools/knowledge_router.py --stage no-such-stage` → argparse 拒绝，`EXIT=2`。

## 7. Prompt 注入检查

逐份阅读安装副本的 `SKILL.md` 与 `references/` 5 个文件：

- 未发现要求执行外部命令、上传/下载数据、访问网络、忽略上层规则或泄露凭据的指令；
- `sources_index.md` 明确"教材 PDF 不得随 Skill 分发"，属于限制而非索取；
- `check_refs.py` 只读本地文件与台账，不联网；
- 结论：**未发现提示注入风险**。剩余风险是规则文本较长，若被整份塞入上下文会挤占预算，应由路由按阶段加载。

## 8. 变更文件清单

| 文件 | 动作 |
|---|---|
| `.opencode/skills/test-design-methodology/**`（7 个文件） | 新建（草案完整复制 + frontmatter 修订） |
| `tools/knowledge_router.py` | 新建 |
| `knowledge/README.md` | 改写为归档导航 + 运行时重定向 |
| `knowledge/08_derived_rules/test_design_decision_rules.md` | 顶部加 ARCHIVE 横幅（正文未删） |
| `knowledge/08_derived_rules/submission_schema.md` | 顶部加 ARCHIVE 横幅（正文未删） |
| `knowledge/08_derived_rules/selenium_agent_rules.md` | 顶部加 PARTIAL 横幅（正文未删） |
| `mooctest-knowledge/decision-rules/README.md` | 规范路径改指已安装 Skill |
| `mooctest-knowledge/reports/INTEGRATION-v0.2.1.md` | 新建（本文件） |
| `mooctest-knowledge/evaluations/RUNTIME_CALL_TEST-20261031.md` | 新建 |
| `.opencode/skills/test-case-design/SKILL.md` | 追加「知识加载顺序」一节 |

未修改：`tests/**`、`tools/evidence.py`、`tools/generate_report.py`、`tools/run_selenium.py`、`tools/env_check.py`、`mooctest-knowledge/skill-drafts/**`、`knowledge/01_*`–`knowledge/07_*`、`docs/**`、`opencode.json`、`AGENTS.md`、`.opencode/commands/**`。

## 9. 剩余风险

1. **单样本试验**：`RUNTIME_CALL_TEST` 每组仅 1 次、非盲评、非真实赛题，不能证明比赛得分提升。
2. **规则双份存在**：草案目录仍保留 v0.2.1 副本（按要求只读），若有人直接编辑草案，会与安装副本漂移；目前只有 `decision-rules/README.md` 的说明约束，没有自动 diff 门禁。
3. **台账与正文一致性**：`check_refs.py` 只校验 `canonical_file` 是否存在，不校验文件内容是否包含对应 rule_id；规则被删但文件仍在时不会报错。
4. **质量门禁未落地**：`submission_schema.md` §6 的 10 条自动校验仍是历史设想，`tools/pre_submission_gate.py` 在本报告写入时不存在。
5. **官方规则未知**：2026 评分细则与 AI 许可未确认，所有优先级均为推断。
