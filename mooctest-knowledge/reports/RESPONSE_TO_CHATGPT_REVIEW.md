# 对 ChatGPT 第二轮评审（v2）的逐项回复

日期：2026-10-29
对象：`CHATGPT_REVIEW_FOR_TRAE_v2.md`、`MOOCTEST_KNOWLEDGE_USAGE_GUIDE_v0.2_REVISED.md`
处置口径：**接受 / 部分接受 / 拒绝**，每项附理由与落地位置。未落地的项明确写"未做"。

---

## 0. 材料更正

| 项 | 处置 | 说明 |
|---|---|---|
| 撤回对《Introduction to Software Testing》缺失的批评 | **接受** | 用户已确认本轮材料为 Myers 3rd + Explore It!。v0.1 中"材料缺口"写法已在 `inventory/source_registry.md` §3.0 改为范围说明；不再要求补齐、不再计为整改项。 |
| 教材分工判断（Myers 管设计、Explore It! 管无规格） | **接受** | 与 v0.1 一致，保留。 |

---

## 1. 五个争议问题

### Q1 无依据预期是否计入正式用例
**处置：接受（采纳 A 为默认，保留 B 的极小例外）。**
- 落地：`test_oracle.md` ORA-04 —— `ORACLE-UNKNOWN` 不得进入 `cases.json`，只进 `observations.json`，不计入覆盖率。
- 例外落地：仅当可定义"有来源、可复核的部分判定"时保留用例并标 `ORACLE-PARTIAL`，且必须写"可验证部分 / 不可验证部分 / 依据"。
- 双统计落地：`test_oracle.md` §2 定义"需求关联度"与"可验证用例覆盖率"，后者为对外主指标。

### Q2 pairwise 无出处是否删除
**处置：接受（不删除，但不设为必选）。**
- 落地：`method_selector.md` MS-05 将出处改为 `[NIST] SP 800-142`，并写明四个前提（参数独立、无穷举约束、存在交互风险、有预算）。
- 保留我的补充判断：**默认 2-way 属工程默认值**，NIST 提供的是组合测试方法学与覆盖强度概念，不等于"2-way 是唯一正确选择"；因此规则里写"默认 2-way，强度由风险评估决定"，并要求题目指定组合优先。

### Q3 探索式是否需要 charter
**处置：接受。**
- 落地：MS-06 改为"**微型** charter"，四字段（目标/范围/停止条件/可转化产物）+ 限时；明确"不建立与正式用例集并行的探索工作流"。
- 增加约束：探索结果必须经 `ORA-01/02` 证据化后才进入正式用例；观察不得升级为缺陷（DEF-10）。

### Q4 37 条是否压缩为 15+22
**处置：部分接受。**
- 接受"15 不是魔法数字"：`decision-rules/README.md` 明确写出 15 条常驻的**入选标准**（能否直接产出可判定、可追溯、不越界的用例），而不是凑数。
- 接受"必须逐条验证无冲突"：本轮已核对核心 15 条两两关系，冲突处置写在 `method_selector.md` §3.2。
- 拒绝"用字符数估算 token 后宣称节省"：v0.2 已删除任何 token 数字声明，改为"未计量"。`SKILL.md` 只给加载顺序，不给伪精确数字。

### Q5 旧 `knowledge/08_derived_rules/` 双份口径
**处置：接受（单一来源）。**
- 落地：新建 `inventory/rule_registry.csv`，含 `rule_id / version / authority / trigger / canonical_file / status / supersedes / notes`。
- 旧文件在台账中登记为 `LEGACY-01 / archived`，并在 `decision-rules/README.md` 注明"非规范，禁止与新规则同时编辑"。
- 说明：本轮**未**删除旧文件（属用户既有资产，且本阶段不应对既有材料做破坏性变更），只做状态标记。

---

## 2. §2 十条具体修改

| # | 意见 | 处置 | 落地 |
|---|---|---|---|
| 1 | 教材定位与证据标注 | **接受** | 每条规则加 `[MY]/[EI]/[ISTQB]/[NIST]/[ENG]/[S-01]` 标签；`source_registry.md` §3.1 引入**页码核验双档**（已核验 / `[页码未核验]`） |
| 2 | "参数≥4 → 判定表优先"不正确 | **接受** | MS-03 触发条件改为"多个业务条件共同决定同一结果且可枚举"；原规则登记为 `MS-03-v0.1 / deprecated`。**保留**条件数仅作为**成本阈值**（>6 时降级），不作为触发依据 |
| 3 | REV"每边界 4 点"不可作普遍门禁 | **接受** | MS-01 改为 2-value / 3-value 覆盖项（依据 ISTQB §4.2.2）；REV-02 改为按覆盖项计数；不可表示邻近值记 `N/A`；旧规则登记 `MS-01-v0.1 / deprecated` |
| 4 | "每条需求≥1用例"改为适用门禁 | **接受** | 新增 MS-00 分诊；REV-01 只对 `可测` 需求设门禁，其余进缺口清单；REV-00 定义分母 |
| 5 | 预期来源与断言分离；执行状态单列 | **接受** | `test_oracle.md` §0 拆两维度；`PASS/FAIL/BLOCKED/NOT_RUN/INCONCLUSIVE` |
| 6 | 不让 Skill 篡改预期 | **接受** | 新增 ORA-09：四类归因（业务缺陷/脚本/环境/规格歧义），改预期须附新证据 |
| 7 | 路径可移植性 | **接受** | 规则正文迁入 `skill-drafts/test-design-methodology/references/`，Skill 自包含；新增 `scripts/check_refs.py` 并**已实际执行通过**（见 §4） |
| 8 | 输出契约减负 | **接受** | SKILL.md §输出约定分"设计/审查/交付"三阶段；审查只出差异；中间结果用 JSON |
| 9 | 实际赛题优先 | **接受** | MS-10 + 使用指南 §2 优先级链（赛题 > 需求 > 业务判据 > 工具 API > 方法论 > 经验） |
| 10 | 归档与版权 | **接受** | `sources/chapter-text/` 标记"私有副本，禁止进入公开仓库/技能包"；Skill 包内只有自写规则与页码锚点 |

---

## 3. 我保留的独立技术判断（与评审意见不同或需补充）

| # | 我的判断 | 理由 |
|---|---|---|
| A | 条件数仍应保留为**降级阈值**（>6 时合并规则或转组合覆盖） | 判定表列数随条件数指数增长是客观成本问题；把它当"触发条件"是错的，当"成本阈值"是必要的 |
| B | `ORACLE-PARTIAL` 计入覆盖率，但必须**同时**报"部分验证用例占比" | 若只按"有判据"一刀切计数，会让只验证了格式合法性的用例看起来等于功能通过 |
| C | 不接受"pairwise 的四前提"被简化成"参数多就用 pairwise" | 独立性与交互风险必须显式判断，否则是最容易产生低价值用例的方法 |
| D | 300+ 行规则正文不进入 SKILL.md，但**必须**随 Skill 分发 | 只发入口、规则留在仓库，会导致 Skill 在别的仓库里失效；评审第 7 条的核心诉求正是自包含 |
| E | 页码核验必须分档，不能整包声称"已核验" | 本次实际逐页核验的是 ch2/ch4 全章、ch10 p.193–206、ch3 p.21–24、EI 的 ch2/ch5/ch13/A2；其余引用只能标未核验 |
| F | 不为"篇幅更短"删除 `defect_discovery` 的清单形态 | 清单可直接用于探索与补漏，改成散文会降低可执行性 |

---

## 4. 已实际执行与未执行（明确区分）

**已执行（可复核）**
1. `python scripts/check_refs.py` → 退出码 0：SKILL.md `version=0.2`；5 个 references 均存在；`rule_registry.csv` 解析出 40 条 active 规则且 `canonical_file` 全部存在。
2. 6 个小样例的规则选择核对 → 6/6 符合 v0.2 预期，详见 `evaluations/sample_runs_v0.2.md`。
3. 全库检索 `顺丰|运费|网点` → 无命中，确认项目内无历史赛题需求文件。

**未执行（未做，也不声称做了）**
1. 真实历史顺丰赛题的需求覆盖与用例质量验证 —— **缺需求文件**，无法进行。
2. 基线 vs v0.2 的 A/B 对照实验 —— 未运行，无任何提升结论。
3. token / 耗时计量 —— 未计量，v0.2 已删除 v0.1 的 token 估算表述。
4. OpenCode 部署、Skill 安装 —— 按本阶段要求不做。
5. 产品级缺陷验证 —— 6 个样例均为规则验证，`test_status` 全部 `NOT_RUN`。

---

## 5. 评审提出但我认为需要澄清的两点

1. **"先做小样例再跑真实赛题"的顺序**：我认同，但真实赛题的"有明确规则答案"往往不存在（赛题需求本身模糊）。建议 A/B 时把"有唯一答案的子集"和"无唯一答案的子集"分开评分，否则评分者会因主观一致性问题压低分数。
2. **"独立 Selenium 工作流负责执行"**：本次 `RUN-20261029-02` 已证明执行链路（pytest + 截图 + manifest）可用，但该链路**尚未接入**本 Skill 的 `cases.json` 字段（缺 `oracle_type/source_ref` 到断言的映射）。这是下一阶段的接口缺口，不是本轮整改项。

---

## 6. 本轮交付清单

| 文件 | 状态 |
|---|---|
| `skill-drafts/test-design-methodology/SKILL.md` | v0.2 修订 |
| `skill-drafts/test-design-methodology/references/{method_selector,test_oracle,coverage_review,defect_discovery,sources_index}.md` | 新增/重写（规范来源） |
| `skill-drafts/test-design-methodology/scripts/check_refs.py` | 新增，已执行 |
| `decision-rules/README.md` + 4 个索引文件 | 改为索引，正文迁移 |
| `inventory/rule_registry.csv` | 新增 |
| `inventory/source_registry.md` | 修订（材料范围、核验分档、S-05） |
| `reports/USAGE_GUIDE_v0.2.md` | 新增，替换 v0.1（已删除） |
| `reports/RESPONSE_TO_CHATGPT_REVIEW.md` | 本文件 |
| `evaluations/sample_runs_v0.2.md` | 新增（6 样例 + 真实系统边界说明） |

---

## 7. 仍需外部决定的问题

1. 真实赛题需求文本能否提供？没有它，"真实案例验证"无法闭环。
2. A/B 的评审方式：单人盲评还是双人交叉？是否接受"规则正确率"与"用例质量分"分开报告？
3. 是否允许把 `references/` 中的规则正文以 CC-BY 或内部许可方式随 Skill 分发（涉及个人使用教材的边界，但不含原文，应可行）。
