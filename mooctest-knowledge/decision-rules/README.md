# decision-rules 索引（v0.2）

> **规则正文已统一收敛到已安装 Skill 目录，本目录不再保留可编辑副本**，以避免"两套规则各自漂移"。
> 规范来源（运行时加载）：`.opencode/skills/test-design-methodology/references/`
> 只读草案源（不再作为加载路径）：`../skill-drafts/test-design-methodology/`（保留供版本对照，禁止据此运行）
> 规则台账：`../inventory/rule_registry.csv`（记录 rule_id、版本、权威来源、当前文件、弃用映射）

| 主题 | 旧路径（本目录） | 规范文件（唯一可编辑，已安装） |
|---|---|---|
| 方法选择 | `method_selector.md`（索引） | `.opencode/skills/test-design-methodology/references/method_selector.md` |
| 预期判据 | `test_oracle.md`（索引） | `.opencode/skills/test-design-methodology/references/test_oracle.md` |
| 覆盖评审 | `coverage_review.md`（索引） | `.opencode/skills/test-design-methodology/references/coverage_review.md` |
| 缺陷发现 | `defect_discovery.md`（索引） | `.opencode/skills/test-design-methodology/references/defect_discovery.md` |

旧的项目级速查表 `knowledge/08_derived_rules/test_design_decision_rules.md` 与其 v0.1 版本已标记为 **archive（非规范）**，理由见 `inventory/rule_registry.csv`。

---

## 核心 15 条（常驻规则集，v0.2）

只有这 15 条建议常驻上下文，其余规则按需加载。选入标准：**直接对应用户能否得到"可判定、可追溯、不越界"的用例**。

| # | 规则 | 归属 | 作用 |
|---|---|---|---|
| 1 | 需求分诊（可测/需澄清/不可执行/范围外） | MS-00 | 决定分母与是否继续 |
| 2 | 按"输入域形态 / 业务条件是否决定结果"选方法 | MS-01..05 触发条件 | 防止用错方法 |
| 3 | 分区后定边界，按 2-value/3-value 产生覆盖项 | MS-01 | 修正"四固定点" |
| 4 | 判定表由"业务条件→结果可枚举"触发，不由参数个数触发 | MS-03 | 修正误触发 |
| 5 | 状态迁移：合法迁移 ≥1，关键非法 ≥1 | MS-04 | 覆盖流程风险 |
| 6 | 组合覆盖需满足四个前提，默认 2-way | MS-05 | 防止无脑 pairwise |
| 7 | 判据四档 + 证据强度 | ORA-01..04 | 区分能断言与不能断言 |
| 8 | 无依据 → 观察项，不计覆盖率 | ORA-04 | 禁止编造 |
| 9 | 用例唯一性（同分区换值不算新用例） | REV-03 | 控量 |
| 10 | 每条用例有可判定通过与失败条件 | REV-07 | 可执行 |
| 11 | 步骤可复现、元素可定位 | REV-06 | 可转脚本 |
| 12 | 停止条件按覆盖项达成，不按用例数 | MS-09 | 防止无限扩张 |
| 13 | 赛题约束优先（范围、数量、命名、工具） | MS-10 | 不越界 |
| 14 | 失败四类归因，禁止为通过而改预期 | ORA-09 | 防止造假 |
| 15 | 执行状态与判据分离，未跑即 NOT_RUN | ORA-00 §0.2 | 防止伪称完成 |

非核心规则（错误猜测细节、charter 流程、缺陷清单细项、白盒覆盖说明）保留在 references 中按需加载。
