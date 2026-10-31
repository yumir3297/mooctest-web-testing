# 来源登记表（Source Registry）

> 本表只登记"实际存在于本项目、且被本次处理过"的材料。
> 未读取全文的材料明确标注读取深度，禁止把"已登记"当成"已验证"。
> **页码约定**：Myers 使用书内印刷页码（`p.xxx` 可核验，见每页页眉 `Page N`）；Explore It! 使用 PDF 物理页序号（`[p.xxx]`）；其他文档使用章节号。

---

## 1. 一级材料（本次精读）

| ID | 材料 | 版本 / 文件 | 本地路径 | 规模 | SHA-256 | 读取深度 | 用途 |
|---|---|---|---|---|---|---|---|
| P3-02 | The Art of Software Testing | 3rd ed., Wiley, 2012（Myers / Badgett / Sandler） | `booook/The Art of Software Testing - 3rd Edition (...).pdf` | 254 PDF 页；正文印刷页 1–232 | `367aba821cdc58617a62096fc68489b1a7d8fd9581fbeea2b04ebc8a7750b0d2` | ch2 全文；ch4 全文；ch10 p.193–206；ch3 p.21–24；ch6、ch7 未精读 | 黑盒/白盒用例设计、测试原则、Web 分层测试 |
| P3-03 | Explore It! | 1st ed., Pragmatic Bookshelf, 2013（Elisabeth Hendrickson） | `booook/Explore It ... (...).pdf` | 175 PDF 页 | `08eb93a42889ee940295139eebe65a0f7a9b6c9acf24c665f24844da9d6fffc8` | ch2、ch5、ch13、附录 A2 全文精读；ch3、ch4、ch6、ch7、ch8 已切分未精读 | 探索式测试、charter、oracle 近似判定、启发式清单 |

### 1.1 章节页码锚点（Myers，已校验）

| 章 | 标题 | 印刷页 | PDF 页 |
|---|---|---|---|
| ch2 | The Psychology and Economics of Software Testing | 5–18 | 19–32 |
| ch3 | Program Inspections, Walkthroughs, and Reviews | 19–40 | 33–54 |
| ch4 | Test-Case Design | 41–84 | 55–98 |
| ch5 | Module (Unit) Testing | 85–112 | 99–126 |
| ch6 | Higher-Order Testing | 113–142 | 127–156 |
| ch7 | Usability (User) Testing | 143–156 | 157–170 |
| ch8 | Debugging | 157–174 | 171–188 |
| ch9 | Testing in the Agile Environment | 175–192 | 189–206 |
| ch10 | Testing Internet Applications | 193–212 | 207–226 |
| ch11 | Mobile Application Testing | 213–232 | 227–254 |

ExplorIt! 章节起点（PDF 页）：ch1=20, ch2=27, ch3=41, ch4=49, ch5=62, ch6=73, ch7=80, ch8=88, ch9=100, ch10=111, ch11=120, ch12=132, ch13=144, A2=161。

---

## 2. 二级材料（项目内已有，未重复处理）

| ID | 材料 | 本地路径 | 状态 | 本次用法 |
|---|---|---|---|---|
| S-01 | 2025 全国大学生软件测试大赛 Web 应用测试赛项说明（评分准则） | `knowledge/01_competition_official/P0-03_2025_web_track_spec_text.txt` | 已读（3 页全文） | 评分维度与交付物约束；**历史基线，不得当作 2026 强制规则** |
| S-02 | ISTQB CTFL Syllabus v4.0.1 | `knowledge/02_istqb/P0-04_ISTQB_CTFL_Syllabus_v4.0.1_text.txt` | 已读 §4.2.2、§4.3.1、§4.3.2 | **BVA 的 2-value / 3-value 覆盖项定义（v0.2 修正依据）**；黑盒技术分类；语句/分支覆盖 |
| S-05 | NIST SP 800-142, Practical Combinatorial Testing | 未下载（仅登记公开出处：`https://csrc.nist.gov/pubs/sp/800/142/final`） | 仅引用其主题定位，未引用具体条款 | 组合覆盖（pairwise 等）的正式公开出处 |
| S-06 | Selenium AI Agents 文档 | `knowledge/03_selenium_pytest/P0-06_selenium_ai_agents_text.txt` | 未复核 | 本轮不涉及，仅登记 |
| S-03 | Selenium 官方文档（waits / test practices / API） | `knowledge/03_selenium_pytest/` | 未复核 | 本次不涉及编码规则，交给 ui-test-selenium |
| S-04 | 2026 报名/复赛通知 | `knowledge/01_competition_official/P0-01..P0-02` | 未复核 | 交付物定义以 2026 通知为准 |

---

## 3. 材料范围与缺口

### 3.0 本轮材料范围（2026-10-29 用户确认，v0.2 生效）

本轮实际研究材料确定为 **《The Art of Software Testing》第 3 版** 与 **《Explore It!》** 两本。
此前任务描述中的《Introduction to Software Testing, 2nd ed.（Ammann & Offutt）》系用户先前材料信息有误所致，**不属于本轮范围，不需要补充、替换或说明缺席**；v0.1 中把它列为"材料缺口"的写法已于 v0.2 撤回。

由此产生的两个后果（保留为技术事实，不作为整改项）：

1. 覆盖准则不使用该书口径，改引 ISTQB CTFL v4.0.1 §4.3（见 S-02）。
2. 组合覆盖的正式公开出处改用 NIST SP 800-142（见 S-05），不再标注"无出处"。

### 3.1 仍需声明的限制

1. **两本 PDF 均含 z-library 站点标识**，属来源可疑的本地副本。
   - 处置：仅作内部方法论参考，**不进入任何交付物、不粘贴原文、不进入公开 Git 仓库或技能分发包**；知识库只记录"方法名 + 自写结论 + 页码锚点"。
2. Myers 书内 PDF 无书签目录，章页映射由页眉 `Page N` 反查，已逐章抽样核验。
3. **页码核验状态分两档**，不得混用：
   - `已核验`：本次实际打开对应页并确认内容（ch2、ch4 全章；ch10 p.193–206；ch3 p.21–24；Explore It ch2/ch5/ch13/A2 指定页）。
   - `未核验`：仅依据切分文本做关键词检索、未逐页比对原文的引用，一律在规则里标注 `[页码未核验]`。
4. 2026 赛题与当届评分细则尚未发布，所有"比赛优先级"结论均为**基于 2025 基线的推断**。
5. **项目内不存在真实历史顺丰赛题需求文件**（已全库检索 `顺丰|运费|网点`，无命中）。因此"真实赛题验证"只能留待用户提供需求文本后执行，本轮不伪造。

---

## 4. 数据处理方式

- 原始 PDF 只读，未修改、未重命名、未移动。
- 按章切分导出纯文本至 `mooctest-knowledge/sources/chapter-text/`，每页保留 `[printed p.N | PDF p.N]` 锚点，便于回溯核验。
- 每页剥离页眉版权行、`www.it-ebooks.info` 水印行与空行；未做内容改写。
- 知识库内所有规则均为自写语言，未整段复制教材正文。

---

## 5. 材料价值判断（摘要）

- **Myers ch4 是本次最高价值材料**：它给出的不是概念解释，而是"输入特征 → 方法 → 用例数量"的可执行流程（p.41–84），其中 p.82–83 的 5 步组合策略可直接改写成 Agent 决策表。
- **Myers ch2 提供判定基线**：预期输出必填（p.13–14）、无效输入优先（p.15）、副作用检查（p.16）、缺陷聚集（p.17）。这四条直接构成 test oracle 与 defect discovery 的骨架。
- **Explore It! 的价值在 oracle 与启发式**：Never/Always、内部一致性、标准、可比软件、近似判定（p.63–70）是目前唯一能覆盖"无明确规格"场景的成体系方法。
- **低价值部分明确排除**：Myers ch8（调试）、ch11（移动端）、A1（面试评估）与 Web 赛道无关。
