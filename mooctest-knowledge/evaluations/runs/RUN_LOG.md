# 运行日志（run log）

日期：2026-10-29
协议：`evaluations/validation_pack_v1/MOOCTEST_SKILL_VALIDATION_PROTOCOL_v1.md`
试题：`evaluations/validation_pack_v1/MOOCTEST_SKILL_TEST_FIXTURES_v1.json`
Skill 版本：`test-design-methodology` **v0.2.1**（SKILL.md frontmatter `version: 0.2.1`）

## 1. 运行配置

| 项 | 值 | 是否满足协议要求 |
|---|---|---|
| 模型 | DeepSeek-V4.1-Flash（当前 Trae 会话模型，A/B 相同） | 满足（同模型） |
| 会话隔离 | 每题每组一个独立 subagent 上下文 | 部分满足：非独立进程，无法保证完全隔离 |
| 温度/采样参数 | **不可设置**（环境未暴露） | **未满足**，无法固定 |
| 提示 | 8 题同一模板，仅需求原文不同；两组模板差异仅为"是否加载 Skill" | 满足 |
| 答案泄漏控制 | 金标准检查表先建（`_gold/checklist_v1.md`），未进入任何提示 | 满足 |
| 文件访问 | A 组禁止读取项目文件；B 组仅允许读 Skill 目录 | 满足（提示约束），实际工具调用不可审计 |
| Tool 一致性 | 两组同为 general-purpose agent | 满足 |
| 运行次数 | 每题每组 **1 次** | **未满足**协议的"建议 3 次" |
| Token 计量 | **不可获得** | **未满足**，仅能给字符数代理 |
| 浏览器/真实执行 | 未使用 | 按 E 阶段处理 → NOT RUN |

## 2. 加载文件（B 组）

| 文件 | 大小 |
|---|---|
| `SKILL.md` | 5.9 KB |
| `references/method_selector.md` | 14.2 KB |
| `references/test_oracle.md` | 7.5 KB |
| `references/coverage_review.md` | 6.7 KB |
| `references/defect_discovery.md` | 5.0 KB |
| `references/sources_index.md` | 2.4 KB |

B 组在 3 处规则修复（MS-01 精度一致性、MS-01 开闭区间、MS-05 第 0 步）与版本号升至 0.2.1 之后运行；其输出中出现 "邻近值必须与字段精度一致，取整数 0/21""下边界 0 是开区间…覆盖项 {−0.1, 0, 0.1}""MS-05 第 0 步" 等原文级证据，可确认加载的是 v0.2.1。

B 组每题至少加载 SKILL.md（5.9 KB）；从输出中出现的规则编号（MS-01/03/04/05/06/09/10、ORA-01/03/04/05/07/09、REV-02/03/04/08/09、DEF-06/07）判断，至少还加载了 method_selector、test_oracle、coverage_review 三份。**具体每题加载了哪几份，subagent 工具调用不可审计 → 未验证。**

## 3. 输出规模（代理指标，非 token）

| 题 | A 组字符数（去空白） | B 组字符数（去空白） |
|---|---:|---:|
| T01 | 858 | 1210 |
| T02 | 1160 | 1835 |
| T03 | 1333 | 1397 |
| T04 | 994 | 1373 |
| T05 | 1004 | 1541 |
| T06 | 1582 | 1369 |
| T07 | 1228 | 1327 |
| T08 | 1514 | 1415 |
| **合计** | **9673** | **11467** |

- 输出侧 B 比 A 多 **18.6%**。
- 输入侧 B 还要额外加载 5.9–38.3 KB 的 Skill 文本（依实际读取份数）。
- **字符数不等于 token**，本报告不据此声称 token 差异。

## 4. 原始产物位置

- A 组原始输出：`evaluations/runs/A_RAW.md`（逐题原文）
- B 组原始输出：`evaluations/runs/B_RAW.md`（逐题原文）
- 金标准检查表：`evaluations/runs/_gold/checklist_v1.md`
- 安装模拟：`evaluations/runs/_install_sim/test-design-methodology/`（用于 S 阶段路径验证）

## 5. 已知偏差与限制（影响结论强度）

1. **单次运行**：无重复，无法估计波动；任一分差可能来自随机性。
2. **非盲评**：金标准与评分由同一执行者完成，存在自我确认偏差。
3. **参数不可控**：温度等未固定，严格意义上不满足"配置一致"。
4. **加载未审计**：无法证明 B 组实际读了哪些 references。
5. **无真实执行**：全部 `NOT_RUN`，不涉及浏览器、Selenium、截图。
6. **样本小**：8 题 × 1 次，不能外推到真实赛题。
