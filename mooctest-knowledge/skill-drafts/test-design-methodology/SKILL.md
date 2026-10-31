---
name: test-design-methodology
description: 在只有需求文档或需求不完整的 Web 功能测试场景下，按"需求分诊 → 方法选择 → 覆盖项定义 → 预期判据 → 覆盖自审"产出可判定、可追溯的测试用例。不负责 Selenium 编码、执行、截图与最终文档排版。
version: 0.2.1
status: draft
---

# 测试设计方法论 v0.2.1（DRAFT）

> 未安装、未接入运行时。本目录自包含：所有规则正文在 `references/`，路径相对本文件解析。
> 依赖校验：`python scripts/check_refs.py`（校验 references 是否齐全、版本是否一致）。

## 何时使用

- 输入是自然语言需求 / 页面说明，要产出**测试用例**（不产出脚本）。
- 需求有缺失或歧义，需要在**不编造规则**的前提下继续推进。
- 需要在提交前自查"漏了什么、重复了什么、哪些预期没依据、哪些没跑"。

## 何时不要使用

| 需求 | 交给 |
|---|---|
| 元素定位、等待策略、脚本框架、Page Object | `ui-test-selenium` |
| 需求拆解、任务排期、测试策略规划 | `breakdown-test` |
| 用例文档的格式规范、文风、文档模板 | `test-case-writing` |
| 用例集的独立评审（外部视角） | `test-case-reviewer` |
| 真实浏览器交互探索取证 | `playwright-cli` |
| 语句/分支覆盖率数字 | 需要源码与覆盖率工具，本 Skill 不提供 |

## 核心决策流程（六步，不可跳步）

1. **需求分诊（MS-00）**
   每条需求标 `可测 / 需澄清 / 不可执行 / 非测试范围`。只有 `可测` 进入后续步骤，其余进缺口清单。
   产出：`requirements.json`（id, text, source, status, constraint）。

2. **方法选择（MS-01..05 触发条件）**
   两个判断轴：**输入域形态**（分区+边界 / 格式枚举）、**业务条件是否决定同一结果**（判定表）。
   有状态机 → 状态迁移；参数独立且有交互风险 → 组合覆盖（默认 2-way）；缺少规格 → 微型 charter。
   **禁止**用参数个数决定是否用判定表。

3. **覆盖项定义（MS-01/MS-03/MS-04）**
   每个边界按选定的 2-value 或 3-value 准则列出 2 或 3 个覆盖项；判定表按可达列；状态机按合法/关键非法迁移。
   产出：覆盖项清单（可数、可复算）。

4. **预期判据（ORA-01..04）**
   四档：`SPEC / DERIVED / PARTIAL / UNKNOWN`。
   `UNKNOWN` **不得**进入正式用例集，只能进 `observations.json`，且不计入覆盖率。
   产出：`cases.json`（case_id, requirement_id, oracle_type, source_ref, expected, judge_rule, test_status=NOT_RUN）。

5. **覆盖自审（REV-00..09）**
   按覆盖项核对，不按用例条数；识别重复；核对"边界取值是否在页面上真实可表示"；统计双指标。
   产出：`coverage_report.json` + 必改项清单。

6. **缺陷风险补充（DEF-01..10）**
   按清单补齐输入异常、参数冲突、顺序状态、页面一致性、动态交互、导航会话、测试假设。
   `[ENG]` 条目只能触发"疑点"，不能单独认定为产品缺陷。

## 重要禁止事项

1. 不得为凑满用例而编造需求中不存在的业务规则、提示文案或输入限制。
2. 不得把行业惯例、其他产品行为、模型经验写成 `ORACLE-SPEC`。
3. 不得把"每边界 4 点"当成通用门禁；覆盖项由分区、精度、开闭区间与所选 BVA 准则决定。
4. 不得在页面无法输入、无邻近可表示值时凭空生成边界数据。
5. 不得在赛题限定的输入范围、角色、数量之外生成正式用例。
6. 不得用"测试功能是否正常""页面正常显示"作为测试目的或通过标准。
7. 不得为让用例通过而修改预期；失败必须先归因（业务缺陷/脚本/环境/规格歧义）。
8. 未实际执行不得写 `PASS`；一律 `NOT_RUN`，执行后用 `PASS/FAIL/BLOCKED/INCONCLUSIVE`。
9. 不得把本 Skill 规则当成赛事官方规则；2026 细则未发布前，比赛优先级均为推断。

## 参考文件入口（按需加载，勿全量读取）

| 需要什么 | 文件 | 建议读法 |
|---|---|---|
| 选方法、定覆盖项、停止条件 | `references/method_selector.md` | 先看 §1 矩阵，再读对应 MS 规则 |
| 预期怎么定、失败怎么归因 | `references/test_oracle.md` | 先看 §0 两维度表 |
| 自查漏没漏、怎么算覆盖率 | `references/coverage_review.md` | 先看 REV-00，再按项核对 |
| 该怀疑哪些 Web 缺陷 | `references/defect_discovery.md` | 直接用 §3 勾选清单 |
| 出处、页码核验状态 | `references/sources_index.md` | 只在被质疑时读 |

规则台账与弃用映射：仓库内 `mooctest-knowledge/inventory/rule_registry.csv`（**不在 Skill 包内**，缺失不影响运行）。

## 输出约定（分阶段，避免每次都产大表）

- **设计阶段**：`requirements.json` → `design_plan.json` → `cases.json`（结构化，机器可读）+ 人读 Markdown 摘要。
- **审查阶段**：只输出差异、发现、建议（按 `coverage_review.md` §3 模板），不重复整表。
- **交付阶段**：由编排层生成 Excel/文档，本 Skill 不产出交付格式。
- 每条正式用例必须具备：`case_id, requirement_id, oracle_type, source_ref, expected, judge_rule, test_status`；执行后补 `evidence_ref`。

## Token 预算（按需加载）

| 场景 | 加载 | 量级 |
|---|---|---|
| 单功能点快速设计 | SKILL + method_selector §1 | 最小 |
| 复杂业务规则 | 再加 test_oracle | 中 |
| 提交前自查 | 再加 coverage_review | 中 |
| 探索阶段 | SKILL + defect_discovery | 中 |

不用字符数估算 token；实际消耗需在评估记录中按模型计量（见 `mooctest-knowledge/evaluations/`）。

## 版本与状态

- 当前 `0.2`，状态 `draft`，未安装、未验证于真实赛题。
- 规则编号不重排；弃用规则见 `rule_registry.csv`，旧编号保留并在表中标 `deprecated`。
