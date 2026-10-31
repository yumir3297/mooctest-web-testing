# 2026 年全国大学生软件测试大赛 Web 应用测试赛道：官方规则整理

- 整理日期：2026-10-31
- 来源：大赛官网《2026年全国大学生软件测试大赛第二轮报名通知！》转发的 B 站官方培训视频，UP 主 `CST_Mooctest`
- 采集方式：三条视频均按 3–4 秒抽帧读取画面（介绍视频的字幕列表为空）；语音讲解未转写。下文时间戳为视频播放位置，文字是画面内容的整理，不是逐字稿。
- 性质：**视频画面整理，不是官方文件**。官方后续通知、赛题包、平台页面与本文不一致时，以官方为准。
- 关联文档：`docs/OFFICIAL_2025.md`（2025 题包格式基线）、`docs/ENVIRONMENT.md`（本机环境基线）

## 0. 视频清单

| 视频 | BVID / URL | 时长 | 本文用途 |
|---|---|---|---|
| 2026年Web应用测试赛项介绍 | `BV1C7Jr66EAK`，https://www.bilibili.com/video/BV1C7Jr66EAK/ | 8:07 | 赛制、评分、提交物、工具版本、比赛流程 |
| 2026Web应用测试环境搭建_Java版本 | `BV1C7Jr66EMc`，https://www.bilibili.com/video/BV1C7Jr66EMc/ | 6:07 | JDK 21、Maven、JUnit、POM、IDEA 配置 |
| 2026Web应用测试环境搭建_Python版本 | `BV16pJr6TEXn`，https://www.bilibili.com/video/BV16pJr6TEXn/ | 4:38 | Python、PyCharm、Selenium 4.49.0、ChromeDriver 配置 |

介绍视频发布于 2026-10-15 09:20:19，属于“2026年全国大学生软件测试大赛-web培训视频”合集的第 1/3 集。

## 1. 赛制与时间

画面位置：介绍视频 00:12。

| 阶段 | 形式 | 比赛时长 | 证书与奖励 |
|---|---|---|---|
| 预选赛 | 线上 | 3 小时 | 不颁发证书及奖励 |
| 省赛 | 线上或线下 | 4 小时 | 颁发证书 |
| 总决赛 | 线下 | 4 小时 | 颁发证书和大赛奖金 |

- 比赛开始：选手在慕测平台下载题目文档。
- 比赛结束：选手根据文档要求在慕测平台上传结果文档。
- 赛道名称：Web 应用测试。

## 2. 评分标准

画面位置：介绍视频 00:56–03:28。总分由测试用例文档、测试脚本、截图文件三部分累加；总分相同则按提交时间二次排序。

| 维度 | 评分点 | 画面要求 |
|---|---|---|
| 测试用例文档 | 充分性 | 用例对测试功能点的覆盖率 |
| 测试用例文档 | 可读性 | 用例标题可读、可理解，清晰易理解 |
| 测试用例文档 | 可复现性 | 操作步骤中的被测元素和操作行为均被清晰、完整描述 |
| 测试脚本 | 代码用例一致性 | 脚本代码与用例描述中的操作步骤一致 |
| 测试脚本 | 代码可运行性 | 无语法错误且可正常运行 |
| 测试脚本 | 代码规范性 | 是否包含自动化测试代码框架所需的几要素 |
| 测试脚本 | 代码可读性 | 参照企业代码质量评估标准 |
| 截图文件 | 关键节点 | 是否精准捕捉关键操作节点及对应页面状态 |
| 截图文件 | 过程呈现 | 是否清晰呈现测试过程中的核心交互和功能验证点 |

脚本还要求：测试脚本与测试用例关联且一致，能稳定运行；根据比赛要求对主要页面自动截图，以便下一步分析。

## 3. 提交物与硬性格式

画面位置：介绍视频 02:32–03:28、07:52–08:04。

| 文件 | 格式 | 大小上限 | 备注 |
|---|---|---|---|
| 测试用例文档 | `.docx` | 10.0 MB | 按官方用例模板填写 |
| 测试脚本压缩包 | `.zip` | 10.0 MB | 不要用 rar |
| 测试截图压缩包 | `.zip` | 50.0 MB | 必须包含 `screenshots/` 目录 |

提交前检查：答案是否都已提交成功，上传的是否为最终版答案。

### 3.1 用例模板字段（10 项）

画面位置：介绍视频 02:32。

1. 测试用例编号：唯一，便于用例管理与追溯
2. 模块名称：明确用例的功能归属，避免模块混淆
3. 需求编号：实现需求与测试用例的双向追溯
4. 用例说明：该条用例主要测试什么
5. 前置条件：执行该用例所需的待测软件状态
6. 执行步骤：操作步骤，描述应符合功能说明书
7. 输入数据：执行该条用例时的输入数据
8. 预期结果：用例正常执行应出现的结果
9. 实际结果：用例正常执行实际出现的结果
10. 截图文件名：与用例步骤对应，便于结果核查

### 3.2 截图文件

画面位置：介绍视频 03:08–03:28。

- 截图区域：整个浏览器窗口。
- 所有截图放在同一个文件夹，文件夹统一命名为 `screenshots`。
- 打包时直接打包这个文件夹，使用 `.zip`，**不要使用 rar**；rar 包将无法解析截图，导致截图部分不得分。
- 一条用例只对应一张截图；调试代码产生的多张时间戳截图要删除，只保留一张有效截图。
- 截图文件名要与用例表中的【截图文件名】字段对应。

### 3.3 测试脚本

画面位置：介绍视频 02:48、07:12、07:32。

- 代码中的函数命名按官方要求；每个测试脚本对应一个或多个测试用例。
- 每个测试用例应能独立运行，不依赖其他测试用例的状态。
- 使用官方模板；代码开头标识注释 `// test-code-start` 和结束标识注释 `// test-code-end`（Python 模板对应 `# test-code-start` / `# test-code-end`）不要删除。
- 官方模板中的 chromedriver 路径在本地调试时改为本地路径；脚本完成、提交前改回官方路径。
- 文件编码 UTF-8。

> 2026 视频只展示了上述模板约束；2025 题包额外要求“一个需求一个测试函数”、截图命名 `<11位时间戳>_<用例编号>.png` 等。2026 赛题包发布后需以包内《注意事项》复核。

## 4. 官方环境要求

### 4.1 Python 路径（本项目采用）

| 组件 | 官方要求 | 视频位置 | 说明 |
|---|---|---|---|
| Python | 3.10.0 版本以上 | Python 视频 00:06 | 官网安装包 |
| PyCharm | 使用 PyCharm 创建项目 | Python 视频 02:12–02:48 | 官方演示 IDE |
| Selenium | `pip install selenium==4.49.0` | Python 视频 03:12 | 视频使用精确版本 4.49.0 |
| pytest | 8.0 版本以上 | 介绍视频 05:08、05:28 | 环境视频未演示安装 pytest |
| Chrome | 150 版本以上 | Python 视频 00:21 | 低于 150 先升级 |
| ChromeDriver | 与 Chrome 版本对应 | Python 视频 00:42–01:33 | 下载 win64 包 |

官方 Python 环境视频的安装顺序：

1. 安装 Python 3.10+。
2. 安装 Chrome，确认版本 ≥ 150。
3. 打开 `googlechromelabs.github.io/chrome-for-testing/`，按 Chrome 版本选择相近的 ChromeDriver；下载 `chromedriver-win64.zip`。
4. 解压到 Chrome 浏览器的 `Application` 目录，并把该目录加入系统 `Path`。
5. 在“服务”中禁用 Google 更新的两个服务，避免 Chrome 自动升级后驱动不匹配。
6. 安装 PyCharm，新建项目，选择本地 Python 解释器。
7. 在 CMD 中执行 `pip install selenium==4.49.0`；若 pip 版本报错，先执行 `python.exe -m pip install --upgrade pip`。
8. 粘贴官方代码模板，按需求编写脚本；解释器报错时在 PyCharm 中切换为本地 Python 解释器。

### 4.2 Java 路径（备选）

| 组件 | 官方要求 | 视频位置 | 说明 |
|---|---|---|---|
| JDK | 21 版本 | Java 视频 00:06 | 用 `java -version`、`javac` 验证 |
| IDEA | IntelliJ IDEA | Java 视频 02:18 | 官方演示 IDE |
| Maven | 3.9 版本以上 | Java 视频 02:18–04:45 | 视频示例路径 `apache-maven-3.9.9`；下载页当时为 3.9.16 |
| Selenium Java | 4.49.0 | Java 视频 05:33 | POM 依赖 |
| JUnit | 5.10 版本以上 | 介绍视频 04:20；POM 5.10.2 | `junit-jupiter-api/engine/params` |
| commons-io | 2.18.0 | Java 视频 05:33 | POM 依赖 |
| Java 编译级别 | 21 | Java 视频 05:24 | `maven.compiler.source/target=21` |
| Chrome | 150 版本以上 | Java 视频 00:27 | 与 Python 路径相同 |
| ChromeDriver | 与 Chrome 版本对应 | Java 视频 00:48–01:39 | 解压到 Chrome `Application` 并加入 `Path` |

官方 Java 环境视频的关键步骤：

1. 安装 JDK 21，配置环境变量，用 `java -version`、`javac` 验证。
2. 按 Python 路径同样的方法安装 Chrome 与 ChromeDriver，禁用 Google 更新服务。
3. 下载 Maven，解压到自定义目录（视频示例 `D:\software\Maven\apache-maven-3.9.9`）。
4. 新建系统变量 `MAVEN_HOME`，在 `Path` 中添加 `%MAVEN_HOME%\bin`，用 `mvn -version` 验证。
5. 在 `conf/settings.xml` 配置本地仓库 `localRepository`，并在 `<mirrors>` 中加入阿里云镜像。
6. 执行 `mvn help:system`，确认本地仓库生成文件。
7. 在 IDEA 中配置 Maven home、User settings file 和本地仓库。
8. 新建 Maven 项目，POM 中加入 Selenium 4.49.0、JUnit 5.10.2、commons-io 2.18.0，编译级别 21。
9. 运行一个 Selenium 示例，确认依赖加载成功。

## 5. 赛前准备与比赛流程

### 5.1 赛前准备

画面位置：介绍视频 06:08。

1. 注册成为慕测网站用户。
2. 报名 Web 应用测试赛项。
3. 下载测试工具。
4. 安装、配置环境（详细步骤参考两条环境搭建视频）。
5. 下载练习题目。
6. 编写测试用例、测试脚本。
7. 执行测试。
8. 提交测试用例、测试脚本和截图文件。

报名页分个人赛/团队赛；填写指导老师信息时，指导老师工号在老师的个人主页获取。团队报名还需要填写团队成员信息。

### 5.2 比赛当天

画面位置：介绍视频 06:56–08:04。

1. 登录慕测网站 `http://www.mooctest.net/#/home`。
2. 进入已报名的 Web 应用测试赛项。
3. 下载题目附件 zip。
4. 题目文件通常包含：注意事项、测试代码模板（Java/Python）、需求文档、测试用例模板、功能说明手册。
5. 在模板的 `test-code-start` / `test-code-end` 之间编写脚本，按需求补全测试用例。
6. 执行测试，按官方要求生成截图。
7. 在比赛结束前上传用例文档、脚本压缩包、截图压缩包，确认提交成功且为最终版。

## 6. 与本项目环境的对照

### 6.1 Python 运行时（本项目正式路径）

实测时间：2026-10-31。命令与完整输出见 `docs/ENVIRONMENT.md` §9。

| 项 | 官方要求 | 本机实测 | 判定 |
|---|---|---|---|
| Python | ≥ 3.10.0 | 3.13.9 | PASS |
| Selenium | 4.49.0（官方安装命令） | 4.51.0 | PASS（高于 4.49.0；已用 4.49.0 回归） |
| pytest | ≥ 8.0 | 9.1.1 | PASS（高于 8.0；已用 8.4.2 回归） |
| Chrome | ≥ 150 | 156.0.8078.76 | PASS |
| ChromeDriver | 与 Chrome 主版本一致 | 156.0.8078.80 | PASS（主版本 156 一致；补丁号不同） |
| PyCharm | 官方演示 IDE | 未在 PATH 与常见安装目录检测到 | 不影响命令行执行；如需完全复刻官方流程可补装 |
| 浏览器驱动路径 | Chrome `Application` + `Path` | 项目内 `tools/driver/chromedriver.exe`，脚本显式指定 | 本地开发可用；提交导出时写回官方路径 |

`python tools/env_check.py` 结果：

```text
verdict: READY  (PASS=17 WARN=0 BLOCKED=0)  exit=0
```

其中驱动来源校验 `driver_source=PASS`，表示 `tools/driver/chromedriver.exe` 的 SHA-256 与 `tools/driver/DRIVER.md` 记录一致。

### 6.2 Java 路径（备选，不计入当前合规结论）

| 项 | 官方要求 | 本机实测 | 判定 |
|---|---|---|---|
| JDK | 21 | 17.0.18（Temurin） | 不满足；仅影响 Java 路径 |
| Maven | ≥ 3.9 | 未安装 | 不满足；仅影响 Java 路径 |
| IDEA | IntelliJ IDEA | 2025.3.3 | PASS |
| JUnit / Selenium Java | 5.10.2 / 4.49.0 | 未验证 | NOT_VERIFIED |

结论：本项目正式自动化使用 Python；Java 路径目前不具备官方要求的 JDK 21 与 Maven，不应声称 Java 环境已合规。若比赛当天需要切 Java，必须先补装并重跑验证。

### 6.3 官方版本兼容性验证（真实执行）

为确认“本机版本更高”不会导致脚本在官方版本下失效，使用隔离虚拟环境安装官方版本组合，执行 TodoMVC 基线：

```powershell
python -m venv .tmp\venv-official
.tmp\venv-official\Scripts\python.exe -m pip install selenium==4.49.0 pytest==8.4.2
.tmp\venv-official\Scripts\python.exe tools\run_selenium.py `
  --run-id RUN-20261031-OFFICIALVER-03 `
  --target https://demo.playwright.dev/todomvc `
  --suite tests\test_todomvc.py `
  --suite tests\test_todomvc_expected_failure.py `
  --capture-pass
```

实测结果：

```text
7 passed, 1 xfailed in 12.12s
exit_code=0  status=passed  tests=8  failures=0  errors=0  xfailed=1
```

证据门禁：`python tools\evidence.py verify --run-id RUN-20261031-OFFICIALVER-03 --fail-on-error` → `checked=15, ok=15, missing=[], mismatched=[], cross_run=[], unscoped=[], duplicates=[]`。

运行环境：Python 3.13.9、Selenium 4.49.0、pytest 8.4.2、Chrome 156.0.8078.76、ChromeDriver 156.0.8078.80。

> 排除记录：`RUN-20261031-OFFICIALVER-01` 误把 `tests/generated/cartcheck` 一并收集，而本地 8765 fixture 未启动，产生 31 个 `ERR_CONNECTION_REFUSED`；该 run 已标记为 `aborted`，不作为兼容性结论。`RUN-20261031-OFFICIALVER-02` 为同一基线的无截图采集版本，结果同为 7 passed + 1 xfailed；本文正式引用带证据的 `-03`。

### 6.4 与官方视频操作方式的差异

| 项 | 官方视频 | 本项目 | 处理 |
|---|---|---|---|
| ChromeDriver 位置 | 解压到 Chrome `Application`，加入 `Path` | 固定 `tools/driver/chromedriver.exe`，Selenium 显式指定 | 本地开发不受影响；官方导出脚本写回 `C:\Program Files\Google\Chrome\Application\chromedriver.exe` |
| Chrome 自动更新 | 建议禁用 Google 更新服务 | 本机没有官方视频中的 `gupdate` / `gupdatem` 服务；已禁用用户级 `GoogleUpdaterTaskUser157.0.8089.0{04D2C338-17C3-428A-B652-1CFC7A91F8F9}` 计划任务（State=`Disabled`） | 已按官方建议关闭；任务名含版本号，赛前复核状态 |
| IDE | PyCharm / IDEA | OpenCode + 命令行 pytest；IDEA 已装 | 不影响运行；如需完全复刻官方界面可补装 PyCharm |
| Python 依赖 | 官方只演示 Selenium 4.49.0 | 锁定 Selenium 4.51.0 + pytest 9.1.1 等 | 已用官方版本回归；无需降级 |
| 驱动路径提交 | 本地改本地、提交前改回官方 | `tools/export_official_2025.py` 生成官方路径 | 打包后仍需人工复核一次 |

> 本机没有 `C:\Program Files\Google\Chrome\Application\chromedriver.exe`（Chrome 为用户级安装），因此该路径只用于提交件；本地运行使用项目内驱动。比赛前需确认官方环境中的实际驱动路径与模板一致。

## 7. 赛前检查清单

- [x] `python tools/env_check.py` 返回 `READY`，退出码 0
- [x] Python ≥ 3.10（实测 3.13.9）
- [x] Selenium ≥ 4.49.0（实测 4.51.0）
- [x] pytest ≥ 8.0（实测 9.1.1）
- [x] Chrome ≥ 150（实测 156.0.8078.76）
- [x] ChromeDriver 与 Chrome 主版本一致（156 / 156）
- [x] 驱动 SHA-256 与 `DRIVER.md` 一致
- [x] Selenium 4.49.0 + pytest 8.4.2 隔离环境回归通过
- [ ] 比赛前复核 Chrome 是否自动升级，驱动是否仍匹配
- [ ] 提交前把脚本中的 chromedriver 路径改回官方路径
- [ ] 在比赛环境确认 `C:\Program Files\Google\Chrome\Application\chromedriver.exe` 存在，或按官方模板要求改为比赛机实际路径
- [ ] 2026 赛题包发布后复核 10 列用例表、一需求一函数、截图命名
- [ ] 如切 Java 路径：JDK 21 + Maven 3.9+ 安装并重跑验证
- [ ] 如需完全复刻官方演示：安装 PyCharm
- [x] 已禁用用户级 GoogleUpdater 计划任务（本机无 `gupdate` / `gupdatem` 服务；赛前复核任务状态）

## 8. 变更记录

| 日期 | 变更 |
|---|---|
| 2026-10-31 | 首次整理三条官方培训视频；完成 Python 路径合规对照与 Selenium 4.49.0 兼容性回归；记录 Java 路径缺口 |
