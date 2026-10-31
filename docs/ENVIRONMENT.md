# 环境与工具链（Environment & Toolchain）

本文件记录本项目的**可复现环境基线**：本机实测版本、驱动来源与校验方式、
`tools/env_check.py` 的用法与退出码约定、升级流程和常见故障。

约定：**「本机实测」= 本机实际执行命令得到的结果**；**「官方要求」= 上游包元数据或
官方文档给出的约束**。两者必须分开写，不得互相代替。

基线日期：2026-10-31（UTC 2026-10-30）。

---

## 1. 实测版本表（本机实测）

| 组件 | 实测版本 | 获取方式 | 备注 |
|---|---|---|---|
| 操作系统 | `Windows-11-10.0.26340-SP0` | `platform.platform()` | x86_64 |
| Python | `3.13.9` (MSC v.1944 64 bit) | `python --version` | 解释器 `C:\Users\<user>\AppData\Local\Programs\Python\Python313\python.exe` |
| Selenium | `4.51.0` | `import selenium; selenium.__version__` | 测试执行核心 |
| pytest | `9.1.1` | `python -m pytest --version` | JUnit XML + xfail |
| openpyxl | `3.1.5` | `importlib.metadata` | xlsx 用例表 |
| Pillow | `12.2.0` | `PIL.__version__` | 截图处理 |
| opencv-python | `5.0.0.93`（运行时 `cv2.__version__` = `5.0.0`） | `importlib.metadata` / `cv2.__version__` | 视觉差异 |
| numpy | `2.4.4` | `numpy.__version__` | 图像数组 |
| Node.js | `v24.14.1` | `node --version` | `D:\nodejs\node.EXE` |
| playwright-cli | `0.1.22` | `node_modules\.bin\playwright-cli.cmd --version` | 未加入系统 PATH，用项目内 `.bin` |
| Chrome | `156.0.8078.74` | PE 版本资源（`chrome.exe`） | 见 §3.1 |
| ChromeDriver | `156.0.8078.80` | `tools\driver\chromedriver.exe --version` | 见 §3 |

实测到的完整驱动版本串：

```text
ChromeDriver 156.0.8078.80 (fb096c0011f9d50f0a264a9376420cdea9c421e3-refs/branch-heads/8078@{#1705})
```

实测到的浏览器会话信息（独立 Selenium 冒烟，§5.2）：

```text
browserName      = chrome
browserVersion   = 156.0.8078.74
chromedriverVersion = 156.0.8078.80 (fb096c0011f9d50f0a264a9376420cdea9c421e3-refs/branch-heads/8078@{#1705})
platformName     = windows
title            = React • TodoMVC
```

## 2. 官方要求 vs 本机实测

上游包元数据（`importlib.metadata` 读取的 `Requires-Python`，本机实测查询）：

| 包 | 官方 `Requires-Python` | 说明 |
|---|---|---|
| selenium 4.51.0 | `>=3.10` | |
| pytest 9.1.1 | `>=3.10` | |
| pillow 12.2.0 | `>=3.10` | |
| opencv-python 5.0.0.93 | `>=3.6` | |
| numpy 2.4.4 | `>=3.11` | **当前锁定组合的实际下限** |
| openpyxl 3.1.5 | `>=3.8` | |

- **有效最低 Python 版本是 3.11**（由 numpy 2.4.4 决定），本机 3.13.9 满足。
- `tools/env_check.py` 的硬门禁写成 **Python < 3.8 → BLOCKED**，这是项目自己的兜底阈值，
  不是上述包的官方要求。两者含义不同：3.8~3.10 不会被 env_check 拦，但装不上下表的锁定版本。
- Chrome 与 ChromeDriver 必须**主版本一致**，这是 ChromeDriver 官方支持矩阵的要求，
  也是本项目审计项 P0-2 的强制门禁。

## 3. 驱动来源与校验

### 3.1 为什么不使用 `chrome.exe --version`

在 Windows 上，若 Chrome 已有运行实例，`chrome.exe --version` 会把命令行转交给现有会话，
实际输出是中文提示（`正在现有的浏览器会话中打开。`），**不含版本号**。
因此 `tools/env_check.py` 在 Windows 上优先读取 PE 版本资源
（`version.dll` + `GetFileVersionInfoW`），实测得到 `156.0.8078.74`；
`--version` 解析与安装目录扫描仅作为降级路径，且会在 `evidence` 字段标注解析方式
（`pe-version-resource` / `cli --version` / `install-dir-fallback`）。

### 3.2 固定驱动

| 项目 | 值 |
|---|---|
| 路径 | `tools/driver/chromedriver.exe` |
| 版本 | `156.0.8078.80` |
| 大小 | `24290304` 字节 |
| SHA-256 | `95AE04AEBD7DAF845DCE58D42139F0ACBF1A5172FD480DB328EA70BDC6301790` |
| 来源 | `https://storage.googleapis.com/chrome-for-testing-public/156.0.8078.80/win64/chromedriver-win64.zip`（HTTP 200） |
| 下载时间 | `2026-10-30T16:42:37Z` |
| 压缩包 SHA-256 | `D9E6AC0F49EAD56069E4809384E21E024BAAA924B6C8BFE0E593506499C57364` |
| 归档旧版 | `tools/driver/archive/chromedriver-155.0.8059.84.exe`（SHA-256 `2D9A190089EC8546E955479B4BA6866EAEA5D63E1AFB050B5B97662F4DBAD41B`） |

完整记录（含升级/回滚步骤）见 `tools/driver/DRIVER.md`。
`tools/env_check.py` 的 `driver_source` 检查项**解析该文件中的 SHA-256**并与磁盘文件比对，
因此升级驱动时必须同步更新 `DRIVER.md`，否则会被判 `BLOCKED`。

### 3.3 依赖锁定

`requirements.txt` 锁定 §1 中已通过回归验证的版本；驱动的版本锁定在 `DRIVER.md`，
Node 侧依赖锁定在 `package.json`。

## 4. `tools/env_check.py`：统一环境诊断

### 4.1 用法

```powershell
python tools\env_check.py                 # 人读报告
python tools\env_check.py --json          # stdout 输出 JSON，人读摘要走 stderr
python tools\env_check.py --strict        # WARN 也视为失败（退出码 3）
python tools\env_check.py --chrome "C:\path\chrome.exe" --chromedriver "D:\path\chromedriver.exe"
```

`--json` 的顶层结构：

```json
{
  "verdict": "READY",
  "strict": false,
  "exit_code": 0,
  "generated_at": "2026-10-30T16:43:54Z",
  "summary": {"PASS": 17, "WARN": 0, "BLOCKED": 0, "total": 17},
  "blocking": [],
  "warnings": [],
  "facts": {"chrome_version": "156.0.8078.74", "chromedriver_version": "156.0.8078.80", "...": "..."},
  "checks": [{"id": "driver_major_match", "status": "PASS", "detail": "...", "evidence": "..."}]
}
```

每个检查项固定四个字段：`id` / `status` / `detail` / `evidence`。

### 4.2 检查项与判定规则

| id | 判定 | 失败态 |
|---|---|---|
| `python_version` | 解释器版本 | `< 3.8` → BLOCKED |
| `selenium` | 真实导入 | 导入失败 → BLOCKED |
| `pytest` | 真实导入 | 导入失败 → BLOCKED |
| `openpyxl` / `pillow` / `opencv` / `numpy` | 真实导入 | 失败 → WARN（只影响视觉/打包） |
| `chrome_binary` | 定位 Chrome 可执行文件 | 找不到 → BLOCKED |
| `chrome_version` | 读取版本（PE 资源优先） | 读不到 → BLOCKED |
| `chromedriver_binary` | 固定路径存在 | 缺失 → BLOCKED |
| `chromedriver_version` | 执行 `--version` | 无法执行 → BLOCKED |
| `driver_major_match` | 主版本比较 | **不一致 → BLOCKED（P0-2 门禁，不降级为 WARN）** |
| `driver_source` | SHA-256 与 `DRIVER.md` 记录比对 | 不一致或记录缺失 → BLOCKED |
| `node` | `node --version` | 缺失 → WARN |
| `playwright_cli` | `node_modules/.bin/playwright-cli --version` 或 PATH | 缺失 → WARN |
| `evidence_dirs` | `evidence/{raw,annotated,diff,logs}`、`reports/executions` | 缺失 → WARN |
| `skills_dir` | `.opencode/skills` 的 7 个项目 Skill、`.agents/skills` 外部 Skill 数量、`knowledge/` 与 `mooctest-knowledge/` | 缺失 → WARN（永不 BLOCKED） |

脚本不硬编码任何期望版本号：所有版本都来自真实探测，只有**最低要求**（Python 3.8）是常量。

### 4.3 verdict 与退出码

| 情形 | verdict | 退出码 |
|---|---|---|
| 全部 PASS | `READY` | `0` |
| 有 WARN、无 BLOCKED | `READY_WITH_WARNINGS` | `0`（`--strict` 时 `3`） |
| 任一 BLOCKED（`--strict` 也一样） | `BLOCKED` | `2` |

CI 或提交前建议用 `python tools\env_check.py --strict`：把「Node/playwright-cli 缺失」
这类会削弱探索取证能力的问题也暴露出来。

### 4.4 Skill 就绪检查

`skills_dir` 检查同时看两侧：

| 侧 | 路径 | 判定内容 |
|---|---|---|
| 项目 Skill | `.opencode/skills/` | 7 个必需 Skill 是否都存在：`browser-exploration`、`mooctest-web-testing`、`selenium-testing`、`test-case-design`、`test-reporting`、`visual-testing`、`test-design-methodology` |
| 外部 Skill | `.agents/skills/` | 目录数量（只报告，不要求具体名称，属于可替换的第三方能力包） |

`detail` 固定写成一行摘要，便于 grep 与日志比对：

```text
project=7 (.opencode/skills) external=5 (.agents/skills), missing=0
```

缺任一项目 Skill 时追加缺失清单，例如：

```text
project=6 (.opencode/skills) external=5 (.agents/skills), missing=1: test-design-methodology
```

**为什么缺失是 WARN 而不是 BLOCKED**：Skill 是 Agent 侧的工作方法文档，不是测试运行时依赖。
缺一个 Skill 不会让 Selenium 会话起不来、不会让 pytest 收集失败、也不会让证据写入失败；
它削弱的只是「按既定方法做事」的能力（例如少了 `test-design-methodology` 就用不上四档 oracle 的分诊流程）。
把它判成 BLOCKED 会让 `env_check.py` 的失败语义失真——BLOCKED 只保留给「跑不起来」的环境问题
（浏览器、驱动、主版本、哈希、核心库）。因此 Skill 缺失一律 WARN，退出码仍为 `0`，
只有在 `--strict` 下才转成 `3`。

## 5. 验证记录（真实执行）

### 5.1 env_check 结果

```text
verdict: READY  (PASS=17 WARN=0 BLOCKED=0)  exit=0

[PASS   ] skills_dir  project=7 (.opencode/skills) external=5 (.agents/skills), missing=0
```

### 5.2 独立 Selenium 冒烟（临时脚本，位于项目外）

脚本 `C:\TempPG\opencode\agentA\smoke_selenium.py` 建立会话 → 打开
`https://demo.playwright.dev/todomvc` → 读标题 → 输入文本并回车 → 点击 checkbox →
`save_screenshot`。实测结果（节选）：

| 断言点 | 实测值 |
|---|---|
| `browserVersion` | `156.0.8078.74` |
| `chromedriverVersion` | `156.0.8078.80 (fb096c...)` |
| `title` | `React • TodoMVC` |
| 新增 todo 后条目数 | `1`，文本 `agent-a smoke item` |
| 勾选前/后 `completed` class | `false` → `true` |
| 剩余计数 | `0` |
| 截图 | `smoke_todomvc_20261030T164424Z.png`，`29459` 字节 |
| 退出码 | `0` |

### 5.3 驱动不匹配的负向验证

把 `tools/driver/chromedriver.exe` 临时替换为归档的 155 版后实测：

```text
[PASS   ] chromedriver_version   155.0.8059.84
[BLOCKED] driver_major_match     chrome major 156 != driver major 155 (...)
[BLOCKED] driver_source          sha256 mismatch vs tools/driver/DRIVER.md (...)
verdict: BLOCKED  (PASS=15 WARN=0 BLOCKED=2)  exit=2
```

恢复 156 驱动后重新执行，`verdict: READY`、退出码 `0`。
`--strict` 的 WARN 路径也已实测（临时从 PATH 移除 node）：
`verdict: READY_WITH_WARNINGS (PASS=15 WARN=2 BLOCKED=0) exit=3`。

### 5.4 TodoMVC 回归

```powershell
python tools\run_selenium.py --run-id RUN-20261031-ENVCHECK-01 `
  --target https://demo.playwright.dev/todomvc --capture-pass --reuse
```

实测结果：

```text
.......x                                                                 [100%]
7 passed, 1 xfailed in 17.58s
exit_code=0  status=passed  tests=8  failures=0  errors=0  xfailed=1  elapsed=19.96s
```

证据门禁：

```text
python tools\evidence.py verify --run-id RUN-20261031-ENVCHECK-01 --fail-on-error
{"checked": 15, "ok": 15, "missing": [], "mismatched": [], "cross_run": [],
 "unscoped": [], "duplicates": []}
exit=0
```

产物位置：

- `evidence/raw/RUN-20261031-ENVCHECK-01/TC-TODO-00{1..7,099}/`
- `evidence/logs/RUN-20261031-ENVCHECK-01/`
- `reports/executions/RUN-20261031-ENVCHECK-01/{junit.xml,junit-summary.json}`

> `run_selenium.py` 默认拒绝复用已存在的 run id，重跑同一 run 需显式加 `--reuse`；
> 这是防止覆盖既有证据的行为，不是环境故障。

### 5.5 版本解析的共用实现

`tests/conftest.py` 通过 `tools/versioning.py`（`find_chrome` / `exe_version` / `major`）
解析浏览器与驱动版本，与 `tools/env_check.py` 内部实现读取同一来源（Windows PE 版本资源）。
两处都**不使用** `chrome.exe --version` 的输出作为唯一依据，原因见 §3.1。

`env_check.py` 故意不 import `versioning.py`：诊断工具必须在测试框架自身损坏时仍能运行，
否则「环境检查」会与被检查对象一起失效。两份实现读取的是同一个系统接口，
版本解析结果一致性由 §5.2 的冒烟结果（`browserVersion=156.0.8078.74`）交叉印证。

### 5.6 Skill 缺失演练（真实执行）

把 `.opencode/skills/test-design-methodology` 临时改名为
`test-design-methodology.disabled`（不删除）后运行：

```text
[WARN   ] skills_dir  project=6 (.opencode/skills) external=5 (.agents/skills), missing=1: test-design-methodology
verdict: READY_WITH_WARNINGS  (PASS=16 WARN=1 BLOCKED=0)  exit=0
warnings: skills_dir
```

改回原名后复核：

```text
[PASS   ] skills_dir  project=7 (.opencode/skills) external=5 (.agents/skills), missing=0
verdict: READY  (PASS=17 WARN=0 BLOCKED=0)  exit=0
```

结论：缺失项目 Skill 只降级为 WARN，`verdict` 变为 `READY_WITH_WARNINGS`，退出码仍为 `0`，
不会被误判成环境故障。

## 6. 升级流程

驱动升级（Chrome 自动更新后必须做）：

```powershell
# 1. 查官方 Stable 版本
#    https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json
# 2. 下载 win64/chromedriver-win64.zip，确认 HTTP 200
# 3. 解压后先验证
.\chromedriver.exe --version
# 4. 归档旧驱动（不删除）
Copy-Item tools\driver\chromedriver.exe tools\driver\archive\chromedriver-<旧版本>.exe
# 5. 覆盖 + 更新 LICENSE.chromedriver
Copy-Item .\chromedriver-win64\chromedriver.exe tools\driver\chromedriver.exe -Force
# 6. 更新 tools\driver\DRIVER.md 的版本、大小、SHA-256、下载 URL、下载时间
# 7. 校验（必须 exit 0）
python tools\env_check.py --json
# 8. 回归
python tools\run_selenium.py --run-id <RUN> --target https://demo.playwright.dev/todomvc --capture-pass
```

Python 依赖升级：先改 `requirements.txt` 的 pin，再 `python -m pip install -r requirements.txt`，
最后 `python tools\env_check.py --strict` + 全量回归。禁止只升版本不跑回归。

## 7. 常见故障

| 现象 | 判定 | 处理 |
|---|---|---|
| `This version of ChromeDriver only supports Chrome version NN` | 主版本漂移 | 按 §6 升级驱动 |
| `env_check.py` 报 `driver_major_match=BLOCKED` | Chrome 自动升级或驱动被替换 | 升级驱动并更新 `DRIVER.md` |
| `env_check.py` 报 `driver_source=BLOCKED` | 驱动文件与 `DRIVER.md` 记录不一致 | 用 `Get-FileHash` 核对；升级未改文档则补文档，文件被篡改则回滚 |
| `chrome_version` 显示 `<empty>` 或中文提示 | Windows 上 `chrome.exe --version` 被转交给已运行实例 | 改用 PE 版本资源读取（`env_check.py` 已内置） |
| 会话启动报 `session not created: DevToolsActivePort file doesn't exist` | 无头模式/权限/杀软拦截 | 加 `--no-sandbox --disable-gpu`，确认驱动可执行 |
| `ModuleNotFoundError: selenium` | 依赖未装或装到了别的解释器 | `python -c "import sys; print(sys.executable)"` 后按 `requirements.txt` 安装 |
| `pytest` 收集不到用例 | 工作目录不对 | 在项目根目录执行，或使用 `python tools\run_selenium.py` |
| `evidence.py verify` 报缺失证据 | 用例未真正落盘证据 | 重跑对应用例，不要手工补 manifest |

## 8. 与审计项的关系

| 审计项 | 本文件对应处置 |
|---|---|
| P0-2 驱动与浏览器主版本不一致 | §3 固定 156.0.8078.80；§4.2 `driver_major_match` 硬门禁；§5.3 负向验证 |
| 环境不可复现 | §1 版本表 + `requirements.txt` 锁定 + `DRIVER.md` 哈希锚定 |
| 无统一自检入口 | §4 `tools/env_check.py`，三档 verdict + 明确退出码 |
