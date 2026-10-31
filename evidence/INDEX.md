# 证据索引

更新时间：2026-10-30T17:53:10+08:00

## RUN-20261029-01 - pytest Selenium acceptance

- 目标：https://demo.playwright.dev/todomvc
- 状态：failed
- 阶段：executed

### TC-TODO-001 test_add_todo

- 状态：passed
- 预期：True
- 实际：断言通过
- 日志：`evidence/logs/RUN-20261029-01/TC-TODO-001.log`
- 证据：
  - [element-screenshot] `evidence/raw/RUN-20261029-01/TC-TODO-001/TC-TODO-001__case__element__20261029T092151-977.png` - 用例证据：新增待办后的元素
  - [fullpage-screenshot] `evidence/raw/RUN-20261029-01/TC-TODO-001/TC-TODO-001__case__fullpage__20261029T092152-065.png` - 用例证据：新增待办后的整页
  - [screenshot] `evidence/raw/RUN-20261029-01/TC-TODO-001/TC-TODO-001__final__viewport__20261029T092152-143.png` - 通过后的最终视口截图

## RUN-20261029-02 - pytest Selenium acceptance

- 目标：https://demo.playwright.dev/todomvc
- 状态：passed
- 阶段：executed

### TC-BROWSER-001 浏览器探索、交互与截图能力验收

- 状态：passed
- 预期：打开 TodoMVC，获取无障碍快照，输入 Acceptance todo，列表出现该文本；视口/整页/元素截图与 MCP 截图均可读取。
- 实际：页面标题 React • TodoMVC；输入后列表出现 Acceptance todo；CLI 与 MCP 截图均为有效 PNG；Playwright MCP 工具列表 25 个。
- 日志：`evidence/logs/RUN-20261029-02/TC-BROWSER-001.log`
- 证据：
  - [snapshot] `evidence/raw/RUN-20261029-01/exploration/snapshot.yml` - 初始页面无障碍快照
  - [snapshot] `evidence/raw/RUN-20261029-01/exploration/after-add.yml` - 新增待办后的无障碍快照
  - [screenshot] `evidence/raw/RUN-20261029-01/browser/viewport.png` - Playwright CLI 视口截图（新增前）
  - [fullpage-screenshot] `evidence/raw/RUN-20261029-01/browser/fullpage.png` - Playwright CLI 整页截图（新增后）
  - [element-screenshot] `evidence/raw/RUN-20261029-01/browser/element-todo-item.png` - 待办项元素截图
  - [element-screenshot] `evidence/raw/RUN-20261029-01/browser/element-footer.png` - 状态栏元素截图
  - [screenshot] `evidence/raw/RUN-20261029-01/mcp/mcp-screenshot.png` - Playwright MCP 截图
  - [snapshot] `evidence/raw/RUN-20261029-01/mcp/mcp-snapshot.yml` - Playwright MCP 无障碍快照
  - [log] `evidence/raw/RUN-20261029-01/mcp/mcp-smoke.json` - Playwright MCP 工具列表与调用结果

### TC-TODO-001 test_add_todo

- 状态：passed
- 预期：True
- 实际：断言通过
- 日志：`evidence/logs/RUN-20261029-02/TC-TODO-001.log`
- 证据：
  - [element-screenshot] `evidence/raw/RUN-20261029-02/TC-TODO-001/TC-TODO-001__case__element__20261029T092211-112.png` - 用例证据：新增待办后的元素
  - [fullpage-screenshot] `evidence/raw/RUN-20261029-02/TC-TODO-001/TC-TODO-001__case__fullpage__20261029T092211-218.png` - 用例证据：新增待办后的整页
  - [screenshot] `evidence/raw/RUN-20261029-02/TC-TODO-001/TC-TODO-001__final__viewport__20261029T092211-289.png` - 通过后的最终视口截图

### TC-TODO-002 test_complete_and_filter

- 状态：passed
- 预期：['Task B']
- 实际：断言通过
- 日志：`evidence/logs/RUN-20261029-02/TC-TODO-002.log`
- 证据：
  - [fullpage-screenshot] `evidence/raw/RUN-20261029-02/TC-TODO-002/TC-TODO-002__Active__fullpage__20261029T092212-060.png` - 用例证据：Active 过滤器结果
  - [screenshot] `evidence/raw/RUN-20261029-02/TC-TODO-002/TC-TODO-002__final__viewport__20261029T092212-127.png` - 通过后的最终视口截图

### TC-TODO-003 test_edit_todo

- 状态：passed
- 预期：['New title']
- 实际：断言通过
- 日志：`evidence/logs/RUN-20261029-02/TC-TODO-003.log`
- 证据：
  - [screenshot] `evidence/raw/RUN-20261029-02/TC-TODO-003/TC-TODO-003__final__viewport__20261029T092213-010.png` - 通过后的最终视口截图

### TC-TODO-004 test_delete_todo

- 状态：passed
- 预期：False
- 实际：断言通过
- 日志：`evidence/logs/RUN-20261029-02/TC-TODO-004.log`
- 证据：
  - [fullpage-screenshot] `evidence/raw/RUN-20261029-02/TC-TODO-004/TC-TODO-004__case__fullpage__20261029T092213-817.png` - 用例证据：删除后的空列表
  - [screenshot] `evidence/raw/RUN-20261029-02/TC-TODO-004/TC-TODO-004__final__viewport__20261029T092213-889.png` - 通过后的最终视口截图

### TC-TODO-005 test_empty_and_whitespace_rejected

- 状态：passed
- 预期：[]
- 实际：断言通过
- 日志：`evidence/logs/RUN-20261029-02/TC-TODO-005.log`
- 证据：
  - [screenshot] `evidence/raw/RUN-20261029-02/TC-TODO-005/TC-TODO-005__final__viewport__20261029T092214-340.png` - 通过后的最终视口截图

### TC-TODO-006 test_boundary_lengths

- 状态：passed
- 预期：['A', 'BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB']
- 实际：断言通过
- 日志：`evidence/logs/RUN-20261029-02/TC-TODO-006.log`
- 证据：
  - [screenshot] `evidence/raw/RUN-20261029-02/TC-TODO-006/TC-TODO-006__final__viewport__20261029T092214-922.png` - 通过后的最终视口截图

### TC-TODO-007 test_text_is_escaped

- 状态：passed
- 预期：None
- 实际：断言通过
- 日志：`evidence/logs/RUN-20261029-02/TC-TODO-007.log`
- 证据：
  - [screenshot] `evidence/raw/RUN-20261029-02/TC-TODO-007/TC-TODO-007__final__viewport__20261029T092215-539.png` - 通过后的最终视口截图

### TC-TODO-099 test_expected_failure_captures_evidence

- 状态：xfailed
- 预期：2 items left
- 实际：tests\test_todomvc_expected_failure.py:22: in test_expected_failure_captures_evidence
    case_ctx.check(page.count_text().startswith("2"), "受控失败断言", "2 items left", page.count_text())
tests\conftest.py:307: in check
    raise AssertionError(f"{name}: expected={expected!r} actual={actual!r}")
E   AssertionError: 受控失败断言: expected='2 items left' actual='1 item left'
- 日志：`evidence/logs/RUN-20261029-02/TC-TODO-099.log`
- 证据：
  - [screenshot] `evidence/raw/RUN-20261029-02/TC-TODO-099/TC-TODO-099__failure__viewport__20261029T092216-142.png` - 失败时视口截图
  - [fullpage-screenshot] `evidence/raw/RUN-20261029-02/TC-TODO-099/TC-TODO-099__failure__fullpage__20261029T092216-142.png` - 失败时整页截图
  - [page-source] `evidence/raw/RUN-20261029-02/TC-TODO-099/TC-TODO-099__failure__page-source__20261029T092216-142.html` - 失败时页面源码
  - [log] `evidence/logs/RUN-20261029-02/TC-TODO-099__browser__20261029T092216-142.log` - 失败时浏览器控制台日志

### TC-VISION-001 模型图像输入与视觉理解能力验收

- 状态：passed
- 预期：模型能识别截图中的圆形复选框和文本 Acceptance todo
- 实际：模型回答：有；图片中显示一个圆形复选框元素，右侧为蓝色文本 Acceptance todo。
- 日志：`evidence/logs/RUN-20261029-02/vision-check-utf8.log`
- 证据：
  - [log] `evidence/logs/RUN-20261029-02/vision-check-utf8.log` - 模型视觉输入实测输出（UTF-16 日志）

### TC-VISUAL-001 截图差异检测、区域定位、裁剪与标注

- 状态：passed
- 预期：对同一视口的新增前/后截图返回非零差异像素和差异区域，生成差异图、热力图、对比图、标注图与裁剪图，原始截图保持不变。
- 实际：检测到 8122 个差异像素（0.8813%），5 个差异区域，最大区域 550x15；派生文件已单独保存，原始截图仍保留在 evidence/raw。
- 日志：`evidence/logs/RUN-20261029-02/TC-VISUAL-001.log`
- 证据：
  - [annotation] `evidence/diff/RUN-20261029-02/TC-TODO-001-before-after/annotated.png` - 差异区域标注图（自动）
  - [comparison] `evidence/diff/RUN-20261029-02/TC-TODO-001-before-after/comparison.png` - 新增前后并排对比图
  - [heatmap] `evidence/diff/RUN-20261029-02/TC-TODO-001-before-after/heatmap.png` - 差异热力图
  - [diff] `evidence/diff/RUN-20261029-02/TC-TODO-001-before-after/diff.png` - 逐像素差异图
  - [metrics] `evidence/diff/RUN-20261029-02/TC-TODO-001-before-after/metrics.json` - 差异指标
  - [regions] `evidence/diff/RUN-20261029-02/TC-TODO-001-before-after/regions.json` - 差异区域坐标
  - [annotation] `evidence/annotated/RUN-20261029-02/TC-TODO-001/new-item-annotated.png` - 新增待办行与状态栏中文标注图
  - [crop] `evidence/annotated/RUN-20261029-02/TC-TODO-001/new-item-crop.png` - 新增待办行裁剪图

## RUN-20261030-175051 - pytest Selenium acceptance

- 目标：https://demo.playwright.dev/todomvc
- 状态：blocked
- 阶段：report-ready

（暂无用例）

## RUN-AUDIT-20261030-01 - 只读审计实时能力验证

- 目标：https://demo.playwright.dev/todomvc
- 状态：passed
- 阶段：audit-live

### TC-AUDIT-CMD-001 OpenCode /web-test --check 命令实调用

- 状态：passed
- 预期：命令可加载 mooctest-web-testing 并输出 WEB_TEST_READY
- 实际：命令实际执行环境检查并输出 WEB_TEST_READY；同时检测到 Chrome 156 与 chromedriver 155 主版本不一致
- 证据：
  - [log] `evidence/logs/RUN-AUDIT-20261030-01/web-test-check.log` - 审计实时验证：/web-test --check 输出日志

### TC-AUDIT-LIVE-001 Playwright MCP 实时交互与取证

- 状态：passed
- 预期：页面标题 React • TodoMVC；输入 Audit todo 20261030 后列表出现该项；计数 1 item left
- 实际：MCP navigate/snapshot/type/evaluate/screenshot 均成功；列表=[Audit todo 20261030]；计数=1 item left
- 证据：
  - [snapshot] `evidence/raw/mcp/page-2026-10-30T09-47-18-037Z.yml` - 审计实时验证：TodoMVC 初始无障碍快照
  - [snapshot] `evidence/raw/mcp/page-2026-10-30T09-47-26-602Z.yml` - 审计实时验证：输入并回车后的无障碍快照
  - [screenshot] `evidence/raw/RUN-AUDIT-20261030-01/TC-AUDIT-LIVE-001/live-viewport.png` - 审计实时验证：输入后的 TodoMVC 视口截图
  - [log] `evidence/raw/mcp/console-2026-10-30T09-47-17-022Z.log` - 审计实时验证：浏览器控制台日志

## RUN-AUDIT-20261030-02 - Selenium acceptance

- 目标：https://demo.playwright.dev/todomvc
- 状态：passed
- 阶段：executed

### TC-TODO-001 test_add_todo

- 状态：passed
- 预期：True
- 实际：断言通过
- 日志：`evidence/logs/RUN-AUDIT-20261030-02/TC-TODO-001.log`
- 证据：
  - [element-screenshot] `evidence/raw/RUN-AUDIT-20261030-02/TC-TODO-001/TC-TODO-001__case__element__20261030T094821-351.png` - 用例证据：新增待办后的元素
  - [fullpage-screenshot] `evidence/raw/RUN-AUDIT-20261030-02/TC-TODO-001/TC-TODO-001__case__fullpage__20261030T094821-450.png` - 用例证据：新增待办后的整页
  - [screenshot] `evidence/raw/RUN-AUDIT-20261030-02/TC-TODO-001/TC-TODO-001__final__viewport__20261030T094821-526.png` - 通过后的最终视口截图

### TC-TODO-002 test_complete_and_filter

- 状态：passed
- 预期：['Task B']
- 实际：断言通过
- 日志：`evidence/logs/RUN-AUDIT-20261030-02/TC-TODO-002.log`
- 证据：
  - [fullpage-screenshot] `evidence/raw/RUN-AUDIT-20261030-02/TC-TODO-002/TC-TODO-002__Active__fullpage__20261030T094822-312.png` - 用例证据：Active 过滤器结果
  - [screenshot] `evidence/raw/RUN-AUDIT-20261030-02/TC-TODO-002/TC-TODO-002__final__viewport__20261030T094822-393.png` - 通过后的最终视口截图

### TC-TODO-003 test_edit_todo

- 状态：passed
- 预期：['New title']
- 实际：断言通过
- 日志：`evidence/logs/RUN-AUDIT-20261030-02/TC-TODO-003.log`
- 证据：
  - [screenshot] `evidence/raw/RUN-AUDIT-20261030-02/TC-TODO-003/TC-TODO-003__final__viewport__20261030T094823-181.png` - 通过后的最终视口截图

### TC-TODO-004 test_delete_todo

- 状态：passed
- 预期：False
- 实际：断言通过
- 日志：`evidence/logs/RUN-AUDIT-20261030-02/TC-TODO-004.log`
- 证据：
  - [fullpage-screenshot] `evidence/raw/RUN-AUDIT-20261030-02/TC-TODO-004/TC-TODO-004__case__fullpage__20261030T094823-950.png` - 用例证据：删除后的空列表
  - [screenshot] `evidence/raw/RUN-AUDIT-20261030-02/TC-TODO-004/TC-TODO-004__final__viewport__20261030T094824-029.png` - 通过后的最终视口截图

### TC-TODO-005 test_empty_and_whitespace_rejected

- 状态：passed
- 预期：[]
- 实际：断言通过
- 日志：`evidence/logs/RUN-AUDIT-20261030-02/TC-TODO-005.log`
- 证据：
  - [screenshot] `evidence/raw/RUN-AUDIT-20261030-02/TC-TODO-005/TC-TODO-005__final__viewport__20261030T094824-528.png` - 通过后的最终视口截图

### TC-TODO-006 test_boundary_lengths

- 状态：passed
- 预期：['A', 'BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB']
- 实际：断言通过
- 日志：`evidence/logs/RUN-AUDIT-20261030-02/TC-TODO-006.log`
- 证据：
  - [screenshot] `evidence/raw/RUN-AUDIT-20261030-02/TC-TODO-006/TC-TODO-006__final__viewport__20261030T094825-153.png` - 通过后的最终视口截图

### TC-TODO-007 test_text_is_escaped

- 状态：passed
- 预期：None
- 实际：断言通过
- 日志：`evidence/logs/RUN-AUDIT-20261030-02/TC-TODO-007.log`
- 证据：
  - [screenshot] `evidence/raw/RUN-AUDIT-20261030-02/TC-TODO-007/TC-TODO-007__final__viewport__20261030T094825-612.png` - 通过后的最终视口截图

### TC-TODO-099 test_expected_failure_captures_evidence

- 状态：xfailed
- 预期：2 items left
- 实际：tests\test_todomvc_expected_failure.py:22: in test_expected_failure_captures_evidence
    case_ctx.check(page.count_text().startswith("2"), "受控失败断言", "2 items left", page.count_text())
tests\conftest.py:309: in check
    raise AssertionError(f"{name}: expected={expected!r} actual={actual!r}")
E   AssertionError: 受控失败断言: expected='2 items left' actual='1 item left'
- 日志：`evidence/logs/RUN-AUDIT-20261030-02/TC-TODO-099.log`
- 证据：
  - [screenshot] `evidence/raw/RUN-AUDIT-20261030-02/TC-TODO-099/TC-TODO-099__failure__viewport__20261030T094826-504.png` - 失败时视口截图
  - [fullpage-screenshot] `evidence/raw/RUN-AUDIT-20261030-02/TC-TODO-099/TC-TODO-099__failure__fullpage__20261030T094826-504.png` - 失败时整页截图
  - [page-source] `evidence/raw/RUN-AUDIT-20261030-02/TC-TODO-099/TC-TODO-099__failure__page-source__20261030T094826-504.html` - 失败时页面源码
  - [log] `evidence/logs/RUN-AUDIT-20261030-02/TC-TODO-099__browser__20261030T094826-504.log` - 失败时浏览器控制台日志

## RUN-CMDCHECK-01 - TodoMVC-CMDCHECK smoke 命令链验证

- 目标：https://demo.playwright.dev/todomvc
- 状态：blocked
- 阶段：blocked

（暂无用例）

## RUN-CMDCHECK-03 - TodoMVC-CMDCHECK3

- 目标：https://demo.playwright.dev/todomvc
- 状态：passed
- 阶段：done

### TC-TODO-001 test_add_todo

- 状态：passed
- 预期：True
- 实际：断言通过
- 日志：`evidence/logs/RUN-CMDCHECK-03/TC-TODO-001.log`
- 证据：
  - [element-screenshot] `evidence/raw/RUN-CMDCHECK-03/TC-TODO-001/TC-TODO-001__exploration__element__20261029T102720Z.png` - 新增 Buy milk 后的待办条目（元素截图）
  - [screenshot] `evidence/raw/RUN-CMDCHECK-03/TC-TODO-001/TC-TODO-001__exploration__viewport__20261029T102721Z.png` - 新增 Buy milk 后的整页视口状态：1 item left 且 footer 可见
  - [snapshot] `evidence/raw/RUN-CMDCHECK-03/TC-TODO-001/TC-TODO-001__exploration__snapshot__20261029T102714Z.yml` - 新增后无障碍快照，确认 textbox/checkbox/filters 结构
  - [log] `evidence/logs/RUN-CMDCHECK-03/TC-TODO-001__browser__20261029T102654Z.log` - 浏览器控制台：仅 favicon.ico 404，无脚本异常
  - [element-screenshot] `evidence/raw/RUN-CMDCHECK-03/TC-TODO-001/TC-TODO-001__case__element__20261029T102736-653.png` - 用例证据：新增待办后的元素
  - [fullpage-screenshot] `evidence/raw/RUN-CMDCHECK-03/TC-TODO-001/TC-TODO-001__case__fullpage__20261029T102736-759.png` - 用例证据：新增待办后的整页
  - [screenshot] `evidence/raw/RUN-CMDCHECK-03/TC-TODO-001/TC-TODO-001__final__viewport__20261029T102736-822.png` - 通过后的最终视口截图

## RUN-TOOLCHECK-01 - 工具调用自检

- 目标：https://demo.playwright.dev/todomvc
- 状态：passed
- 阶段：toolcheck-complete

### TC-TODO-001 test_add_todo

- 状态：passed
- 预期：True
- 实际：断言通过
- 日志：`evidence/logs/RUN-TOOLCHECK-01/TC-TODO-001.log`
- 证据：
  - [element-screenshot] `evidence/raw/RUN-TOOLCHECK-01/TC-TODO-001/TC-TODO-001__case__element__20261029T095511-879.png` - 用例证据：新增待办后的元素
  - [fullpage-screenshot] `evidence/raw/RUN-TOOLCHECK-01/TC-TODO-001/TC-TODO-001__case__fullpage__20261029T095511-974.png` - 用例证据：新增待办后的整页
  - [screenshot] `evidence/raw/RUN-TOOLCHECK-01/TC-TODO-001/TC-TODO-001__final__viewport__20261029T095512-047.png` - 通过后的最终视口截图

### TC-TOOL-BROWSER-001 Playwright CLI 全链路工具自检

- 状态：passed
- 预期：打开 TodoMVC；快照、输入、勾选、悬停、求值、缩放、视口/整页/元素截图、控制台/网络、状态保存、标签页切换均成功。
- 实际：全部成功；items=1 checked=1 count='0 items left'；截图 1280x720/1024x768/550x59 均可读取。
- 日志：`evidence/logs/RUN-TOOLCHECK-01/TC-TOOL-BROWSER-001.log`
- 证据：
  - [snapshot] `evidence/raw/RUN-TOOLCHECK-01/browser/snapshot-before.yml` - Playwright CLI snapshot
  - [snapshot] `evidence/raw/RUN-TOOLCHECK-01/browser/snapshot-after.yml` - Playwright CLI snapshot
  - [screenshot] `evidence/raw/RUN-TOOLCHECK-01/browser/before-viewport.png` - Playwright CLI screenshot
  - [screenshot] `evidence/raw/RUN-TOOLCHECK-01/browser/after-viewport.png` - Playwright CLI screenshot
  - [fullpage-screenshot] `evidence/raw/RUN-TOOLCHECK-01/browser/after-fullpage.png` - Playwright CLI fullpage-screenshot
  - [element-screenshot] `evidence/raw/RUN-TOOLCHECK-01/browser/after-element.png` - Playwright CLI element-screenshot
  - [log] `evidence/logs/RUN-TOOLCHECK-01/browser-console.log` - Playwright CLI log
  - [log] `evidence/logs/RUN-TOOLCHECK-01/browser-requests.log` - Playwright CLI log
  - [log] `evidence/logs/RUN-TOOLCHECK-01/localstorage.log` - Playwright CLI log
  - [log] `evidence/logs/RUN-TOOLCHECK-01/state.json` - Playwright CLI log

### TC-TOOL-EVIDENCE-001 证据管理器 CLI 自检

- 状态：passed
- 预期：start-run/update-case/add-defect/summary/register/verify/index 均可执行；临时虚拟缺陷在验证后清理。
- 实际：add-defect 在临时运行中生成 1 条虚拟缺陷并统计为 defect_count=1；随后删除临时运行；正式运行未登记产品缺陷。
- 日志：`evidence/logs/RUN-TOOLCHECK-01/evidence-add-defect.log`
- 证据：
  - [log] `evidence/logs/RUN-TOOLCHECK-01/evidence-add-defect.log` - add-defect 自检日志

### TC-TOOL-IMAGE-001 图像 inspect/差异/裁剪/标注工具自检

- 状态：passed
- 预期：inspect 读取尺寸；相同图差异为 0；受控差异返回区域；裁剪和中文标注成功；原始图不变。
- 实际：相同图 0 像素/no-change；前后图 7981/921600（0.866%）、6 区域、PSNR 31.0085；裁剪 550x48、标注图生成。
- 日志：`evidence/logs/RUN-TOOLCHECK-01/TC-TOOL-IMAGE-001.log`
- 证据：
  - [screenshot] `evidence/raw/RUN-TOOLCHECK-01/browser/diff-before.png` - 图像工具源图 diff-before.png
  - [screenshot] `evidence/raw/RUN-TOOLCHECK-01/browser/diff-after.png` - 图像工具源图 diff-after.png
  - [annotation] `evidence/diff/RUN-TOOLCHECK-01/identical/annotated.png` - identical annotation
  - [comparison] `evidence/diff/RUN-TOOLCHECK-01/identical/comparison.png` - identical comparison
  - [heatmap] `evidence/diff/RUN-TOOLCHECK-01/identical/heatmap.png` - identical heatmap
  - [diff] `evidence/diff/RUN-TOOLCHECK-01/identical/diff.png` - identical diff
  - [mask] `evidence/diff/RUN-TOOLCHECK-01/identical/mask.png` - identical mask
  - [metrics] `evidence/diff/RUN-TOOLCHECK-01/identical/metrics.json` - identical metrics
  - [regions] `evidence/diff/RUN-TOOLCHECK-01/identical/regions.json` - identical regions
  - [annotation] `evidence/diff/RUN-TOOLCHECK-01/changed/annotated.png` - changed annotation
  - [comparison] `evidence/diff/RUN-TOOLCHECK-01/changed/comparison.png` - changed comparison
  - [heatmap] `evidence/diff/RUN-TOOLCHECK-01/changed/heatmap.png` - changed heatmap
  - [diff] `evidence/diff/RUN-TOOLCHECK-01/changed/diff.png` - changed diff
  - [mask] `evidence/diff/RUN-TOOLCHECK-01/changed/mask.png` - changed mask
  - [metrics] `evidence/diff/RUN-TOOLCHECK-01/changed/metrics.json` - changed metrics
  - [regions] `evidence/diff/RUN-TOOLCHECK-01/changed/regions.json` - changed regions
  - [crop] `evidence/annotated/RUN-TOOLCHECK-01/image/new-item-crop.png` - 裁剪图
  - [annotation] `evidence/annotated/RUN-TOOLCHECK-01/image/new-item-annotated.png` - 中文标注图

### TC-TOOL-MCP-001 Playwright MCP 扩展工具自检

- 状态：passed
- 预期：MCP 服务可初始化；navigate/type/wait/find/snapshot/click/evaluate/resize/console/network/tabs/screenshot/close 全部成功。
- 实际：25 个工具；14 个调用步骤全部成功；evaluate 返回 items=1 checked=1 count='0 items left'；截图 1024x768 有效。
- 日志：`evidence/logs/RUN-TOOLCHECK-01/TC-TOOL-MCP-001.log`
- 证据：
  - [screenshot] `evidence/raw/RUN-TOOLCHECK-01/mcp/mcp-fullpage.png` - MCP 整页截图
  - [snapshot] `evidence/raw/RUN-TOOLCHECK-01/mcp/mcp-snapshot.yml` - MCP 无障碍快照
  - [log] `evidence/raw/RUN-TOOLCHECK-01/mcp/mcp-toolcheck.json` - MCP 工具调用结果 JSON

### TC-TOOL-OPENCODE-001 OpenCode 当前会话工具自检

- 状态：passed
- 预期：skill/task/glob/grep/webfetch/read image 可用；命令文件可枚举；图片可读取。
- 实际：skill visual-testing 加载成功；task explore 返回 6 skills/5 commands；glob 找到命令文件；grep 找到 READY 标记；webfetch 返回 Example Domain；read image 成功显示截图。
- 日志：`evidence/logs/RUN-TOOLCHECK-01/TC-TOOL-OPENCODE-001.log`
- 证据：
  - [log] `evidence/logs/RUN-TOOLCHECK-01/TC-TOOL-OPENCODE-001.log` - 当前会话工具自检日志

