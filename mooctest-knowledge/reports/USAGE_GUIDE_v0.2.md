# 知识库使用指南 v0.2

> 状态：**草案（未部署、未在真实赛题验证）**。取代 `USAGE_GUIDE_DRAFT.md`（v0.1，已删除）。
> 面向未来 OpenCode 使用，但当前阶段不安装 Skill、不改 OpenCode 配置。

---

## 1. 定位与教材边界

本轮确认材料：**《The Art of Software Testing》第 3 版** 与 **《Explore It!》**。
《Introduction to Software Testing》不属于本轮范围（用户 2026-10-29 更正），不再作为缺口或整改项。

| 教材 | 负责什么 | 不负责什么 |
|---|---|---|
| Myers | 黑盒用例设计（分区/边界/判定表）、缺陷导向思维、无预期即非有效用例 | 无规格场景的判定 |
| Explore It! | 需求不全时的探索、Never/Always 与近似判据、风险清单 | 交付级用例结构；观察可升级为"已证实缺陷" |

职责划分：本知识库只负责"**需求 → 可判定用例**"；执行、截图、证据追溯由 Selenium 工具链负责。

---

## 2. 资料优先级（冲突时按此裁决）

```
当届赛题与提交规则
  > 需求文档与明示约束
  > 可核实的业务判据（含赛题样例值）
  > 工具官方 API（Selenium/Pytest）
  > 方法论规则（本知识库）
  > 经验与示例
```

- 规则与示例**永不替代**缺失的业务规格。
- 冲突写入 `ambiguities`，**不得**自动补规则。

---

## 3. 目录与路径契约（v0.2 修正）

规则正文已收敛进 Skill 目录，Skill 自包含：

```
mooctest-knowledge/
  skill-drafts/test-design-methodology/     # 唯一规范来源（未来复制到 .agents/skills/）
    SKILL.md
    references/{method_selector,test_oracle,coverage_review,defect_discovery,sources_index}.md
    scripts/check_refs.py
  inventory/{source_registry.md,rule_registry.csv}
  decision-rules/                            # 仅索引，不含正文
  methods/testing_methodology.md
  examples/, evaluations/, reports/
  sources/chapter-text/                      # 私有教材切分文本，禁止分发
```

**路径解析规则（必须由安装方校验，不交给模型猜）**
1. Skill 内部引用一律相对 `SKILL.md` 所在目录（`references/…`），可在任意工作目录运行。
2. 只在需要"规则台账 / 原文核对"时才访问仓库内 `mooctest-knowledge/inventory/` 与 `sources/`；缺失时 Skill 仍可独立工作。
3. 安装后立即执行 `python scripts/check_refs.py`，退出码 0 才算可迁移；失败则报错，不做静默降级。
4. 若目标环境不支持脚本，至少人工核对：5 个 references 文件存在、`SKILL.md` 的 `version` 与规则台账一致。

---

## 4. 阶段调用与退出条件

| 阶段 | 输入 | 加载 | 退出条件 |
|---|---|---|---|
| 0 明确约束 | 赛题、提交说明 | 仅 SKILL.md | 允许范围、交付形式、技术栈已记录 |
| 1 需求分诊 | 需求 | SKILL + `MS-00` | 每条需求标 `可测/需澄清/不可执行/范围外` |
| 2 选方法 | `requirements.json` | `method_selector.md` §1 | 每个 `可测` 需求有方法与覆盖项类型 |
| 3 定预期 | 需求、规则 | `test_oracle.md` §0 | 每条用例有 `oracle_type + source_ref` |
| 4 生成用例 | 方法与预期 | 交给 `test-case-writing` | `cases.json` 字段齐备 |
| 5 覆盖审查 | 用例与需求 | `coverage_review.md` | 双指标 + 缺口清单产出 |
| 6 有条件探索 | 需求缺失/冲突 | `playwright-cli` + `defect_discovery.md` + `MS-06` | 微 charter 限时结束；观察回流 |
| 7 执行 | 已审用例 | `ui-test-selenium` + Pytest | 实际运行，证据对应用例 ID |
| 8 交付检查 | Excel/源码/截图 | 独立确定性校验脚本 | 文件完整、证据可追溯 |

本 Skill 在阶段 6 只产出观察项，**不**建立与正式用例并行的探索工作流。

---

## 5. Oracle 与执行状态（两个维度分开存）

| 判据类型 | 含义 | 是否计入可验证覆盖率 |
|---|---|---|
| `ORACLE-SPEC` | 赛题/需求明示 | 计入 |
| `ORACLE-DERIVED` | 可复算规则链推导 | 计入 |
| `ORACLE-PARTIAL` | 只有部分性质可验证 | 计入（但须声明验证范围） |
| `ORACLE-UNKNOWN` | 无可靠判据 | **不计入**，只进 `observations.json` |

执行状态独立字段：`NOT_RUN / PASS / FAIL / BLOCKED / INCONCLUSIVE`。
平台状态名不同则记录映射，不强行统一。

---

## 6. 质量门禁

1. 不编造输入限制、提示文案、DOM 选择器。
2. 需求模糊不得被模型常识覆盖。
3. 重复步骤/截图不能冒充不同功能的验证。
4. 断言必须对应可验证 oracle；失败先归因，**不得**为 PASS 改预期。
5. 每条正式用例具备 `requirement_id, case_id, oracle_type, source_ref, test_status`；执行后补 `evidence_ref`。
6. 未执行一律 `NOT_RUN`。
7. 文件名、目录、技术栈必须在当届规则确证后才写死。

---

## 7. 双指标统计

- **需求关联度** = 有用例关联的 `可测` 需求 ÷ `可测` 需求总数。
- **可验证用例覆盖率** = 有 SPEC/DERIVED/PARTIAL 判据的用例所覆盖的 `可测` 需求 ÷ `可测` 需求总数（对外主指标）。
- 单列：观察项数、虚构预期数（必须 0）、`BLOCKED` 数。

禁止用"用例总数 / 需求总数"冒充覆盖率。

---

## 8. Token 与成本

- 每阶段只加载 1–2 个 references 文件。
- 中间结果用结构化 JSON 传递，避免把整张表反复塞进上下文。
- **不用字符数估算 token**；需按模型实际计量并记录（当前未做，见 `evaluations/sample_runs_v0.2.md`）。

---

## 9. 版本与未验证范围

| 项 | 状态 |
|---|---|
| 规则选择（6 个小样例） | 已核对 6/6（规则正确性，非产品执行） |
| references 路径自检 | 已执行，`check_refs.py` 通过 |
| 真实赛题 A/B | **未执行**（无赛题需求文件） |
| 真实系统端到端 | 仅历史 `RUN-20261029-02`（TodoMVC），非本轮规则驱动 |
| OpenCode 部署 | **未部署**，按要求不在本阶段进行 |

---

## 10. 明确不要做

1. 不要把 `examples/` 的业务数值当作真实规则。
2. 不要让模型"总结整本书"；规则可执行，摘要不可执行。
3. 不要把 `sources/chapter-text/` 暴露进公开仓库或技能包（版权）。
4. 不要在本阶段安装 Skill 或改动 OpenCode 配置。
5. 不要在未做 A/B 前宣称质量提升。
