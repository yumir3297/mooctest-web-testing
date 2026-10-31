# 材料处理与质量审查报告

日期：2026-10-29
范围：仅材料预处理与知识工程，未开发工作流、未安装 Skill、未调用任何比赛接口。
结论状态：**知识库可用作方法论基线；验证实验未执行；比赛优先级为推断。**

---

## 1. 材料实际情况（与任务假设的差异）

| 任务清单中的材料 | 实际状态 |
|---|---|
| Introduction to Software Testing, 2nd ed.（Ammann & Offutt） | 项目内不存在。**经用户 2026-10-29 确认，该书不属于本轮研究范围，不作为缺口或整改项**（用户先前材料信息有误）。 |
| The Art of Software Testing, 3rd ed.（Myers 等） | 存在，可读，254 PDF 页 |
| 其他（ISTQB / Selenium / Pytest / 赛事资料） | 存在 ISTQB CTFL v4.0.1 与 2025 赛项说明；Selenium/Pytest 资料存在但本次未复核 |

**因此**：覆盖准则引 Myers ch4 + ISTQB §4.3；组合测试引 NIST SP 800-142（S-05）。v0.1 曾把"pairwise 无出处"标为工程经验，v0.2 已有正式公开出处。

额外发现：项目中还有《Explore It!》（原登记为 P3-03 书目），本次已纳入并成为 oracle 与启发式的唯一来源。

---

## 2. 处理过程

1. 核查：读取 PDF 元数据、页数、书签、页眉页码，建立章-页映射（Myers 用页眉 `Page N`，逐章抽样核验）。
2. 切分：按章导出纯文本至 `sources/chapter-text/`，每页保留 `[printed p.N | PDF p.N]` 锚点；原始 PDF 未改动。
3. 精读：Myers ch2 全文、ch4 全文、ch10 p.193–206、ch3 p.21–24；Explore It ch2、ch5、ch13、A2 全文。未精读的章节只做切分，不据此提炼规则。
4. 交叉核对：ISTQB v4.0.1 §4.2/§4.3；2025 赛项评分准则。
5. 提炼：4 个决策规则文件（共 37 条规则：MS 10 + ORA 8 + REV 9 + DEF 10）、1 个方法论文件、1 个示例集（6 场景）、1 份实验设计、1 个 Skill 草案、3 份报告。
6. 自审：对规则做重复性、可追溯性、误用风险检查（见 §4）。

---

## 3. 重要研究发现

1. **Myers 的真正价值不是"方法清单"，而是"组合顺序"**。ch4 p.82–83 给出的五步策略（组合→边界→等价类→错误猜测→覆盖）直接决定了 Agent 的调度顺序，比单独解释等价类有用得多。
2. **边界值必须代入判定表列，而不是新增用例**。ch4 p.80 的"23 个边界条件并入 37 条用例而不增加用例数"是控制用例爆炸的教材级依据，已成为 MS-03 的核心。
3. **因果图的首要产出是"规格歧义"，不是用例**。ch4 p.79 的示例说明建模过程能暴露需求冲突，这为"需求解析能力"提供了可执行手段，而非泛泛而谈。
4. **无规格场景只有探索式测试能给成体系的 oracle**。Explore It 的 Never/Always（p.63–65）、内部一致性（p.66）、标准与可比软件（p.66–67）、近似判定（p.68–70）四层，恰好补齐 Myers "必须有规格"的硬约束（ch10 p.200）。
5. **教材没有覆盖"题目限定范围"这一比赛特有约束**。MS-10 完全无出处，属工程规则，已显式标注。
6. **Web 专属材料薄弱**。Myers ch10 主要讲分层与挑战（p.195–198），Explore It 的 Web 启发式只有两条（A2 p.166）。真正的 Web 表单/动态交互风险清单只能靠工程经验补齐（DEF-06/07/09）。

---

## 4. 质量审查

### 4.1 规则重复检查
- MS-01 与 MS-02 在"无效类"上有重叠：已通过"格式类字段走 MS-02、纯数值走 MS-01"划界。
- ORA-05 与 ORA-02 在"底线断言"上有重叠：已明确 ORA-05 仅用于无规格情形。
- REV-02 与 MS-08 在方法覆盖上重叠：REV-02 是检查项，MS-08 是生成顺序，保留但注明关系。

### 4.2 错误推断检查
- 初稿曾把"成对覆盖"写成 ISTQB 方法 → 已删除该归属，改为工程实践。
- 初稿在 S3 示例中让保价费参与满减 → 与自设规则冲突，已修正并作为反例记录。
- 初稿将"金额四舍五入"设为默认 → 需求未定义，已改为"待澄清"。

### 4.3 不必要复杂化检查
- 已删除"多浏览器 × 多延迟档位"的场景设计（赛题环境为单一 Chrome）。
- 已拒绝把 Myers ch6/ch7 的全部内容纳入规则（与 Web 交付物无关，仅保留为可查材料）。

### 4.4 可追溯性检查（v0.2 更新）
- 规则台账 `inventory/rule_registry.csv`：active 40 条，弃用 8 条（含 v0.1 的 MS-01/03/05/09、ORA-04、REV-01/02 旧口径）。
- 所有 active 规则的 `canonical_file` 均存在，已由 `scripts/check_refs.py` 实际校验通过。
- 标 `[ENG]`（无标准出处）的规则：MS-10、REV-03、REV-05、REV-00、ORA-09、DEF-08、DEF-09 的具体检查项。
- 页码核验分两档记录：已核验 / `[页码未核验]`，不整包声称。

---

## 5. 版权与数据处理说明

1. 两本 PDF 含 z-library 标识，来源可疑；**仅作内部方法参考**，未复制正文段落进知识库，未进入任何交付物，未对外分发。
2. 知识库只保留"方法名 + 自写结论 + 页码锚点"；引用最短必要短语（≤8 词）用于定位。
3. 原始教材文件未修改、未重命名、未移动。
4. 若后续需公开提交，建议移除 `sources/chapter-text/` 与两本 PDF，仅保留自写规则与书目信息。

---

## 6. 产出文件清单（v0.2）

| 文件 | 状态 | 说明 |
|---|---|---|
| `inventory/source_registry.md` | v0.2 | 材料范围、页码核验分档、S-05 |
| `inventory/rule_registry.csv` | v0.2 新增 | 规则台账（40 active / 8 deprecated / 1 archived） |
| `methods/testing_methodology.md` | v0.2 | BVA 改覆盖项口径；pairwise 改 NIST 出处 |
| `decision-rules/README.md` | v0.2 新增 | 索引 + 核心 15 条 |
| `decision-rules/{method_selector,test_oracle,coverage_review,defect_discovery}.md` | v0.2 | **改为索引**，正文迁入 Skill |
| `skill-drafts/test-design-methodology/SKILL.md` | v0.2 draft | 六步流程、禁令、输出分阶段 |
| `skill-drafts/test-design-methodology/references/*.md` | v0.2 新增 | **唯一规范来源**（5 个文件） |
| `skill-drafts/test-design-methodology/scripts/check_refs.py` | v0.2 新增 | 已实际执行通过 |
| `examples/web_test_scenarios.md` | v0.2 | S1 改 3-value；S5/S6 的 UNKNOWN 移入观察项 |
| `evaluations/evaluation_plan.md` | v0.2 | 双指标 + 覆盖项达成率评分 |
| `evaluations/sample_runs_v0.2.md` | v0.2 新增 | 6 个小样例规则核对 |
| `reports/USAGE_GUIDE_v0.2.md` | v0.2 | 取代已删除的 v0.1 草案 |
| `reports/RESPONSE_TO_CHATGPT_REVIEW.md` | v0.2 新增 | 逐项评审回复 |
| `reports/REVIEW_FOR_CHATGPT.md` | 已废弃 | 仅历史记录 |
| `sources/chapter-text/*.txt` | 15 个文件 | 私有副本，禁止分发 |

---

## 7. 未解决的问题

1. ~~Ammann & Offutt 缺失，覆盖准则与组合测试的权威性不足~~ → **v0.2 已撤回**：该书不在本轮范围；覆盖准则引 ISTQB §4.3，组合测试引 NIST SP 800-142。
2. 2026 赛题与评分细则未发布，默认优先级可能失效。
3. 缺乏真实赛题需求文本，规则无法在真实约束下验证。
4. 规则总量（v0.2 为 40 条 active + 15 条核心常驻）是否过重，需通过消融实验确认。
5. 探索式测试在正式比赛（限时、限交付物）中能占多少比重，尚无依据。
6. ~~2025 赛项说明与 `knowledge/08_derived_rules/` 双份口径~~ → **v0.2 已处置**：建 `inventory/rule_registry.csv` 作为台账，旧文件登记为 `archived`，正文不再双份编辑。文件本身未删除（属用户既有资产）。
7. **项目内无真实历史顺丰赛题需求文件**（全库检索无命中），"真实案例验证"无法闭环，需用户提供。

---

## 8. 验证状态声明

- 全部用例、场景、实验**均未执行**；无截图、无运行日志、无覆盖率数据。
- 本报告不含任何"已验证提升"的结论。

---

## 9. v0.2 修订记录（2026-10-29，回应 ChatGPT 第二轮评审）

**已落地**
1. 材料范围更正：撤回 Ammann 缺口表述；不再要求补齐。
2. `MS-01` 由"每边界四固定点"改为 2-value / 3-value 覆盖项（ISTQB §4.2.2）；旧规则标 `deprecated`。
3. `MS-03` 触发条件由"参数 ≥4"改为"业务条件可枚举且共同决定同一结果"；条件数仅作 >6 的降级阈值。
4. `MS-05` 出处改为 NIST SP 800-142，并加四前提。
5. 新增 `MS-00` 需求分诊；`REV-00` 覆盖门禁口径；`REV-01/02` 按可测性与覆盖项重写。
6. `test_oracle` 拆"判据强度 / 执行状态"两维度；`ORACLE-UNKNOWN` 移出正式用例集、不计覆盖率；新增 `ORA-09` 失败归因。
7. 规则正文迁入 Skill `references/`，Skill 自包含；新增 `scripts/check_refs.py` 并**实际执行通过**（errors=0）。
8. 新增 `inventory/rule_registry.csv`（单一来源台账）。
9. 新增 `reports/USAGE_GUIDE_v0.2.md`（替换 v0.1）、`reports/RESPONSE_TO_CHATGPT_REVIEW.md`、`evaluations/sample_runs_v0.2.md`。

**实际执行的验证（可复核）**
- `check_refs.py`：5 个 references 齐全、SKILL version=0.2、台账 40 条 active 且 canonical_file 均存在 → 通过。
- 6 个小样例规则选择核对：6/6 符合 v0.2 预期（`evaluations/sample_runs_v0.2.md`）。
- 全库检索确认无顺丰赛题需求文件。

**未执行**
- 真实赛题 A/B、token 计量、OpenCode 部署、Skill 安装、产品级缺陷验证。

**未做破坏性变更**
- 未删除 `knowledge/08_derived_rules/`、未修改教材 PDF、未改动 `.agents/skills/` 与 `.opencode/`。
