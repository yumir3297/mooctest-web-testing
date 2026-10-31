# 知识库获取与验证报告（DOWNLOAD REPORT）

- 执行日期：2026-10-28
- 执行范围：`mooctest_reference_download_manifest.md` 的 P0 → P4
- 边界：仅建设知识库；未修改业务代码、未重装已有 Skills、未生成任何比赛提交物、未访问任何付费墙或绕过验证

---

## 一、总体结果

| 状态 | 数量 | 说明 |
|---|---|---|
| 成功获取（原件或可引用正文） | 16 | P0-01~P0-11、P1-01、P1-02、P2 拦截证据 |
| 仅保留链接 / 书目 | 7 | P1-03~P1-06、P3-01~P3-03 |
| 已安装（未重复安装） | 3 | P4-01、P4-02、P4-03 |
| 可选未安装 | 2 | P4-04、P4-05 |
| 原创产出 | 3 | `08_derived_rules/` 三份规则 |
| **失败/阻塞** | 3 | P2-01、P2-02、P2-03（Cloudflare 拦截） |

---

## 二、成功下载并落地的资料

| ID | 资料 | 类型 | 本地路径 | 大小 | 说明 |
|---|---|---|---|---|---|
| P0-01 | 2026 报名及赛项通知 | 网页（SPA） | `01_competition_official/P0-01_2026_signup_notice_text.txt` | 2.8 KB | 服务端返回空壳，用浏览器渲染后提取正文 |
| P0-02 | 2026 第二轮报名通知 | 网页（SPA） | `01_competition_official/P0-02_2026_second_round_notice_text.txt` | 2.6 KB | 同上 |
| P0-03 | 2025 Web 应用测试赛项说明（评分准则） | PDF（A 类） | `01_competition_official/P0-03_2025_web_track_spec.pdf` | 189 KB / 3 页 | 官方直链可下载；同时生成 `_text.txt` |
| P0-04 | ISTQB CTFL Syllabus v4.0.1 | PDF（A 类） | `02_istqb/P0-04_ISTQB_CTFL_Syllabus_v4.0.1.pdf` | 1.06 MB / 79 页 | 官方免费发布，已验证 PDF 有效 |
| P0-05 | ISTQB CTFL 认证页 | 网页 | `02_istqb/P0-05_istqb_ctfl_page_text.txt` | — | 仅索引用 |
| P0-06 | Selenium：Using AI coding agents | 网页 | `03_selenium_pytest/P0-06_selenium_ai_agents_text.txt` | — | 官方对 AI Agent 使用 Selenium 的说明 |
| P0-07 | Selenium llms.txt | 文本索引 | `03_selenium_pytest/P0-07_selenium_llms.txt` | — | 作为按需检索入口，未镜像整站 |
| P0-08 | Selenium Waits | 网页 | `03_selenium_pytest/P0-08_selenium_waits_text.txt` | — | 显式/隐式等待与 sleep 问题 |
| P0-09 | Selenium Test Practices | 网页 | `03_selenium_pytest/P0-09_selenium_test_practices_text.txt` | — | 独立性、Page Object、截图 |
| P0-10 | Selenium Python API | 网页 | `03_selenium_pytest/P0-10_selenium_python_api_text.txt` | — | 核对现行 API |
| P0-11 | pytest How-to 索引 | 网页 | `03_selenium_pytest/P0-11_pytest_howto_index_text.txt` | — | fixture / 参数化 / 断言 |
| P1-01 | 慕测「软件测试专项」课程大纲 | SPA 渲染文本 | `06_mooctest_courses/P1-01_studytrack_text.txt` | 1.4 KB | 公开目录可读，视频需登录（未抓取） |
| P1-02 | 慕测「软件测试工具」课程大纲 | SPA 渲染文本 | `06_mooctest_courses/P1-02_studytool_text.txt` | 1.1 KB | 含 Selenium 元素定位/等待章节索引 |

所有文件的 SHA-256 已写入 `knowledge/00_source_registry.csv`（共 31 条登记）。

## 三、仅可保存链接的资料（合规原因）

| ID | 资料 | 链接 | 原因 |
|---|---|---|---|
| P1-03 | 2026 赛项题库/练习页 | https://www.mooctest.net/student/contest/13 | 需登录；赛题属受控内容 |
| P1-04 | Web 赛项介绍视频 | https://www.bilibili.com/video/BV1C7Jr66EAK/ | 视频平台内容，需在线观看 |
| P1-05 | Python 环境搭建视频 | https://www.bilibili.com/video/BV16pJr6TEXn/ | 同上 |
| P1-06 | Java 环境搭建视频 | https://www.bilibili.com/video/BV1C7Jr66EMc/ | 同上，低优先级 |
| P3-01 | Introduction to Software Testing, 2nd ed. | Cambridge 官方页 | 付费教材 |
| P3-02 | The Art of Software Testing, 3rd ed. | Wiley 官方页 | 付费教材 |
| P3-03 | Explore It! | O'Reilly 官方页 | 订阅制教材 |

## 四、失败项目（FAILED / BLOCKED）

| ID | 标准 | 现象 | 处理 |
|---|---|---|---|
| P2-01 | ISO/IEC/IEEE 29119-3:2021 | Python 直连返回 403；浏览器渲染 12 秒后仍停留在人机验证页 | 未绕过；保留拦截证据 `P2-01_iso29119-3_rendered_raw.txt` |
| P2-02 | ISO/IEC/IEEE 29119-4:2021 | 同上 | 保留证据文件 |
| P2-03 | ISO/IEC 25010:2023 | 同上 | 保留证据文件 |

结论：三项均为**付费标准 + 反自动化访问**，属于合法不可获取范围，已在 `04_iso_public_summaries/README.md` 记录可用概念级信息，未伪造正文。

## 五、需要人工处理（NEEDS_USER_ACTION）

1. **P1-03 赛题导出**：由你登录慕测平台，自行下载 2026 Web 赛项题目与附件，放入 `knowledge/01_competition_official/` 并告知我更新 registry。
2. **P1-04~P1-06 视频**：由你观看后口述要点，或提供官方讲义；当前只保留链接。
3. **P3 教材**：如学校有电子版权限，可导出章节摘录（命名 `P3-0x_用户授权_*.pdf`）后再登记。
4. **P2 标准**：如学校订阅 ISO 标准库，可导出授权副本。
5. **2026 评分细则**：本次只拿到 2025 版赛项说明（含评分准则）。2026 正式评分细则若发布，请补充；在此之前一切评分相关规则都按「历史基线」标注。

## 六、验证结果

| 验证项 | 方法 | 结果 |
|---|---|---|
| 文件完整性 | 逐文件读取、PDF 用 PyMuPDF 打开并提取文本 | 4 个 PDF/文本类均成功解析；P0-03 3 页、P0-04 79 页 |
| 路径正确性 | 脚本检查 16 个落地文件 + 3 个原创文件全部存在 | 全部 EXISTS |
| 来源与版本 | 每个文件记录 URL、发布方、版本、访问日期 | 31 条全部登记 |
| SHA-256 | 对 txt/pdf 计算并写入 CSV | 16 条已记录；未落地项标「不适用」 |
| 索引可用性 | `03_selenium_pytest/00_index.md` 指向 6 个本地文件 | 全部命中 |
| 动态页处理 | SPA 页面使用 playwright-cli 渲染后提取 innerText | P0-01/02、P1-01/02 均成功（无登录数据） |
| 许可证合规 | 逐项填写「许可证/使用限制」列 | 付费教材/标准未下载正文；PolyForm Noncommercial 已标注 |

## 七、知识提炼产出

| 文件 | 内容 | 依据 |
|---|---|---|
| `08_derived_rules/test_design_decision_rules.md` | 输入特征 → 方法选择决策表；粒度/追溯/仲裁/出口准则 | ISTQB CTFL v4.0.1 §4.2；2025 赛项说明；ISO 29119-4 公开概念 |
| `08_derived_rules/selenium_agent_rules.md` | 版本约束、探索边界、定位优先级、等待条件表、断言、异常与重试、失败码、日志取证、结构规则 | Selenium 官方 AI/AI-agents、Waits、Test Practices、Python API；pytest How-to |
| `08_derived_rules/submission_schema.md` | ID 规范（REQ/TC/RUN/SHOT）、五层映射、Excel 列定义、目录布局、10 条自动校验 | 2025 评分准则 + 2026 交付物要求 + ISO 29119-3 追溯概念 |

三份文件均为**原创改写**（决策规则、字段表和校验清单），未复制教材或标准正文段落，每条规则带来源编号。

## 八、事实与推断的边界

- **可作为事实引用**：`01`–`07` 目录中的抓取内容与 registry 记录。
- **属于本库判断**：`08_derived_rules/` 为工程化改写，不是官方规则。
- **不得当作 2026 强制要求**：2025 赛项说明中的所有评分表述，仅作历史基线。
- 截至本报告日期，2026 赛项的**正式评分细则尚未公开获取**，相关结论需在赛题发布后复核。
