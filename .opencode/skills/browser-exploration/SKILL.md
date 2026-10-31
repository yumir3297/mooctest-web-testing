---
name: browser-exploration
description: 用 Playwright 探索真实 Web 页面：无障碍快照、DOM 结构、稳定定位、交互路径、控制台/网络观察和探索证据归档。适用于打开目标站点、确认元素可定位、验证业务流程和截图取证。
license: MIT
compatibility: opencode
metadata:
  audience: test-engineer
  workflow: browser-exploration
---

# browser-exploration

先读 `docs/WORKFLOW.md`、`docs/CONVENTIONS.md`。

## 工具选择

1. 若当前会话已启用 Playwright MCP（`browser_*` 工具），优先用它做持续探索。MCP 的调用会正常返回，适合 Agent 自动化。
2. **子 Agent 会话里 MCP 浏览器通常未连接**（`browser.disconnected: No desktop browser is connected to this session`）。此时不要反复重试，改用 Selenium 写一个**只读探索脚本**（放在 `pipeline_runs/<run>/explore.py`，不要放进 `tests/`），输出标题、关键元素、选择器、控制台日志，并把截图直接保存到 `evidence/raw/<run>/EXPLORE/` 后再登记。
3. 若 MCP 不可用，也可使用项目内已安装的 Microsoft `playwright-cli`。注意：`playwright-cli open` 的进程可能不返回（会话已建立但父进程持有句柄），不要在 Agent 自动化中直接调用 `open`；优先复用已有会话。
4. 不要同时启动多个浏览器会话；一个运行复用一个 `-s=<session>`。
5. 不要为了“齐全”重复安装浏览器 MCP/插件。

### 已知 MCP 行为差异（2026-10-31 实测）

- `browser_fill` 会**追加**而不是替换文本：填表前先清空输入框。
- `browser_press("Enter")` 可能不触发表单提交：优先点击真实按钮。
- `browser_screenshot` 需要标签页可见：先 `browser_tabs_focus`。
- 截图落在 server-local 临时目录，必须复制到 `evidence/raw/<run>/<case>/` 再登记。

## 探索流程

1. 打开页面，记录 URL、标题、视口。
2. `snapshot` 获取无障碍树；用 `find "文本"` 或 `--depth` 局部定位，避免整页大快照反复进入上下文。
3. 从快照拿 ref，再确认稳定选择器（`id`、`data-testid`、稳定 CSS、role+name）；避免绝对 XPath。
4. 执行一次真实交互（输入/点击/提交），再次快照确认状态变化。
5. 需要视觉证据时再截图；优先元素截图，整页截图只在布局相关时使用。
6. 记录控制台错误与失败请求（`console`、`requests`），不要把敏感 Cookie/令牌写入日志。
7. 关闭或保留会话按任务需要；结束时 `close`，不要留下孤儿进程。

## 命令速查

```powershell
npx --no-install playwright-cli -s=<session> open <URL> --browser=chrome
npx --no-install playwright-cli -s=<session> snapshot --filename=evidence/raw/<run>/<case>/snapshot.yml
npx --no-install playwright-cli -s=<session> find "登录"
npx --no-install playwright-cli -s=<session> fill <ref> "文本" --submit
npx --no-install playwright-cli -s=<session> click <ref>
npx --no-install playwright-cli -s=<session> screenshot <ref> --filename=evidence/raw/<run>/<case>/element.png
npx --no-install playwright-cli -s=<session> screenshot --full-page --filename=evidence/raw/<run>/<case>/fullpage.png
npx --no-install playwright-cli -s=<session> console
npx --no-install playwright-cli -s=<session> requests
npx --no-install playwright-cli -s=<session> close
```

Windows 下 URL 含 `&` 时使用 `--%` 或转义，避免被 PowerShell 截断。

## 证据

- 快照：`kind=snapshot`，保存到 `evidence/raw/<run>/<case>/`。
- 截图：`kind=screenshot|fullpage-screenshot|element-screenshot`。
- 控制台/网络：`kind=log`，保存到 `evidence/logs/<run>/`。
- 每份证据登记：

```powershell
python tools/evidence.py register --run-id <RUN_ID> --case-id <CASE_ID> --kind snapshot --path <PATH> --bucket raw --caption "登录页快照"
```

## 输出

- `reports/executions/<run>/exploration.md`：页面清单、关键元素、稳定选择器、交互路径、风险点、未覆盖路径。
- 证据路径与快照文件。
- 给 Selenium 的定位建议：选择器、等待条件、需要清理的状态。

## 边界

- 只访问已授权目标；不进行漏洞扫描、爆破、越权尝试。
- 不修改业务数据，除非赛题允许且使用测试账号。
- 截图前遮蔽密码、令牌、个人信息。
- 页面行为异常先记录证据，不急着下缺陷结论。
