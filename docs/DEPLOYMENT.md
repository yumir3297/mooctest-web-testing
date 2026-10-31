# 部署与重新部署指南

本文件记录本次实际安装/复用的组件、位置和验证命令。目标环境：Windows 11 + OpenCode Desktop 1.19.3（V1 配置体系）。

## 1. 前置条件

| 组件 | 本次版本 | 检查命令 |
|---|---|---|
| OpenCode Desktop | 1.19.3 | 应用内版本信息 / `E:\OpenCode\OpenCode.exe` |
| Node.js | 24.14.1 | `node --version` |
| npm / npx | 11.11.0 | `npm --version`、`npx --version` |
| Python | 3.13.9 | `python --version` |
| Git | 2.53.0 | `git --version` |
| Chrome | **156.0.8078.74** | `chrome://version`（实测路径 `%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe`） |
| ChromeDriver | **156.0.8078.80** | `tools\driver\chromedriver.exe --version` |

> 上表是 2026-10-31 实测值。版本会漂移，**以 `python tools/env_check.py` 的实时输出为准**；详细说明见 `docs/ENVIRONMENT.md`。
> 2026-10-31 晚复核：Chrome 已自动更新到 `156.0.8078.76`（主版本 156 未变），ChromeDriver 仍为 `156.0.8078.80`，`env_check` 判定 `READY`。
> 历史记录：2026-10-29 时为 Chrome 155.0.8059.86 / Driver 155.0.8059.84；本次已升级驱动并归档旧版至 `tools/driver/archive/`。

Python 未加入系统 PATH 时，使用绝对路径：

```text
C:\Users\<user>\AppData\Local\Programs\Python\Python313\python.exe
```

## 2. Python 依赖

本次已存在并复用，不需要重复安装：

```powershell
python -m pip install selenium==4.51.0 pytest==9.1.1 pillow==12.2.0 opencv-python==5.0.0.93 numpy==2.4.4
```

验证：

```powershell
python -c "import selenium,pytest,PIL,cv2,numpy; print(selenium.__version__, pytest.__version__, PIL.__version__, cv2.__version__, numpy.__version__)"
```

## 3. 浏览器驱动

Selenium Manager 在本机曾出现联网解析挂起，因此固定驱动：

```text
tools\driver\chromedriver.exe
```

驱动版本必须与 Chrome 主版本一致（本次 155）。`tests/conftest.py` 已显式使用该路径；文件不存在时才回退到 Selenium Manager。

## 4. Playwright CLI（浏览器主通道）

项目内已有：

```powershell
npm install --save-dev --save-exact @playwright/cli@0.1.22
npx --no-install playwright-cli --version
```

用途：无障碍快照、元素定位、交互、视口/整页/元素截图、控制台/网络观察。官方 README 建议编码 Agent 优先用 CLI+Skills，减少 MCP 工具 schema 的上下文开销。

## 5. Playwright MCP（命令链通道）

项目内已安装并验证：

```powershell
npm install --save-dev --save-exact @playwright/mcp@0.0.83
node tools\mcp_smoke.js
```

`opencode.json` 中当前 `enabled: true`（完整命令链演练使用 MCP）。25 个工具会占用上下文；不需要时可改回 `false`。

1. 将 `opencode.json` 的 `"enabled"` 设为 `true`；
2. 重启 OpenCode Desktop；
3. 用 `npx -y opencode-ai@1.19.3 mcp list` 或 TUI 确认 `playwright` 已连接；
4. 在会话中使用 `browser_navigate`、`browser_snapshot`、`browser_take_screenshot` 等工具。

MCP 启动命令已固定：

```text
node node_modules/@playwright/mcp/cli.js --headless --browser chrome --isolated --viewport-size 1280x720 --output-dir evidence/raw/mcp
```

## 6. OpenCode 项目配置

- 全局配置：`C:\Users\<user>\.config\opencode\opencode.jsonc`（未修改；备份在 `C:\TempPG\opencode-config-backup\opencode.jsonc.20261029.bak`，含凭据，未复制进项目）。
- 项目配置：`opencode.json`（只增加 MCP 配置，不覆盖全局模型/Provider）。
- 项目规则：`AGENTS.md`。
- Skills：`.opencode/skills/<name>/SKILL.md`。
- Commands：`.opencode/commands/<name>.md`。

合并验证：

```powershell
npx -y opencode-ai@1.19.3 debug config
npx -y opencode-ai@1.19.3 debug skill
npx -y opencode-ai@1.19.3 mcp list
```

注意：Desktop 已运行的会话不会热加载新 Skills/Commands；修改后重启 Desktop。CLI 新会话会直接读取项目配置。

## 7. 首次运行

```powershell
# 1) 初始化证据目录
python tools\evidence.py init

# 2) 运行 Selenium 验收
python tools\run_selenium.py --run-id RUN-20261029-02 --target https://demo.playwright.dev/todomvc --capture-pass

# 3) 校验证据
python tools\evidence.py verify --run-id RUN-20261029-02 --fail-on-error

# 4) 生成报告
python tools\generate_report.py --run-id RUN-20261029-02
```

## 8. 常用命令

```powershell
# 新运行
python tools\evidence.py start-run --run-id RUN-YYYYMMDD-HHMMSS --target <URL>

# 视觉差异
python tools\visual_diff.py compare baseline.png actual.png --out-dir evidence/diff/<run>/<case> --label "<case>"

# 裁剪/标注
python tools\visual_diff.py crop image.png --box x,y,w,h --out evidence/annotated/<run>/<case>/crop.png
python tools\visual_diff.py annotate image.png --box "x,y,w,h,标签,#d93025" --out evidence/annotated/<run>/<case>/annotated.png

# 证据索引
python tools\evidence.py index

# OpenCode 命令（CLI）
npx -y opencode-ai@1.19.3 run --command web-test --auto "target=<URL> run_id=<RUN>"
```

## 9. 常见问题

| 现象 | 原因/处理 |
|---|---|
| `opencode` 不在 PATH | Desktop 自带运行时；用 `npx -y opencode-ai@1.19.3` 执行 CLI 验证，或把 CLI 加入 PATH |
| PowerShell 显示中文乱码 | PS 5.1 控制台编码问题；文件本身为 UTF-8/UTF-16。用 Python `encoding='utf-8'` 或编辑器打开验证 |
| `playwright-cli open` 命令不返回 | 会话已建立但守护进程持有句柄；不要在 Agent 自动化中直接 open，改用 MCP `browser_navigate`；手动场景用 `playwright-cli list` 确认后继续 `snapshot/screenshot/close` |
| ChromeDriver 版本不匹配 | 用 `tools\driver\chromedriver.exe --version` 与 Chrome 主版本对齐 |
| MCP 工具不可见 | 确认 `opencode.json` 的 `enabled` 为 `true`，重启 Desktop，并用 `npx -y opencode-ai@1.19.3 mcp list` 检查连接 |
| 命令未出现在 TUI | 确认 `.opencode/commands/*.md` 存在；重启 Desktop；或用 CLI `run --command` 验证 |
| 报告标题中文乱码 | 用 UTF-8-BOM 保存 CSV；用 `report.md`/`report.html` 而非控制台输出检查 |
| 测试污染 | 每个用例清理 localStorage；不要复用同一浏览器 profile 的登录态 |

## 10. 安全

- 不修改被测业务代码。
- 不把凭据写入测试、日志或截图。
- 原始截图只增不改；标注图/差异图单独存放。
- 只测试授权目标；比赛前确认 AI 工具合规要求。
