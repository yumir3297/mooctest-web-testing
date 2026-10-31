# TodoMVC 测试用例（模块 TodoMVC-CMDCHECK3）

- 目标：https://demo.playwright.dev/todomvc
- 运行：RUN-CMDCHECK-03
- 范围：scope=smoke（执行 TC-TODO-001），设计覆盖正常/异常/边界
- 需求来源：TodoMVC 官方演示页（React 版本）可观察行为。未提供正式需求文档，以下验收标准为基于页面行为的显式假设。

## 1. 需求与假设

| 编号 | 需求/假设 | 验收标准 | 风险 |
|---|---|---|---|
| R1 | 新增待办（正常） | 输入文本回车后，列表新增一项，剩余计数为 `1 item left`，底部状态栏可见 | 高 |
| R2 | 完成与过滤 | 勾选后剩余计数更新；All/Active/Completed 过滤结果符合状态 | 高 |
| R3 | 编辑待办 | 双击进入编辑，回车保存新标题 | 中 |
| R4 | 删除待办 | 悬停显示删除按钮，点击后条目移除；列表空时状态栏隐藏 | 中 |
| R5 | 空/空白输入（异常） | 空字符串或纯空白回车不新增条目 | 高 |
| R6 | 长度边界 | 1 字符接受；200 字符完整保存 | 低 |
| R7 | 特殊字符转义（安全输入） | HTML 片段按纯文本展示，不执行脚本 | 中 |
| R8 | 批量切换与清除完成项 | Toggle all 全选；Clear completed 仅移除已完成项（未纳入 smoke） | 中 |
| R9 | 刷新持久化 | 刷新后列表内容保留（localStorage）（未纳入 smoke） | 低 |

## 2. 用例

### TC-TODO-001 新增待办
- 优先级：P0；需求：R1；自动化：`tests/test_todomvc.py::test_add_todo`
- 前置：清空 localStorage 后打开页面
- 数据：`Buy milk`
- 步骤：1) 打开页面 2) 在 `input.new-todo` 输入 `Buy milk` 并回车
- 预期：列表文本为 `["Buy milk"]`；计数为 `1 item left`；`footer.footer` 可见
- 证据：元素截图 + 整页截图 + 运行日志

### TC-TODO-002 完成状态与过滤器
- 优先级：P0；需求：R2；自动化：`tests/test_todomvc.py::test_complete_and_filter`
- 数据：`Task A`、`Task B`
- 步骤：新增两项 → 勾选第一项 → 切换 Completed → 切换 Active
- 预期：计数 `1 item left`；Completed 仅 `["Task A"]`；Active 仅 `["Task B"]`

### TC-TODO-003 编辑标题
- 优先级：P1；需求：R3；自动化：`tests/test_todomvc.py::test_edit_todo`
- 步骤：新增 `Old title` → 双击标题 → 改为 `New title` → 回车
- 预期：列表文本为 `["New title"]`

### TC-TODO-004 删除待办
- 优先级：P1；需求：R4；自动化：`tests/test_todomvc.py::test_delete_todo`
- 步骤：新增 `Delete me` → 悬停 → 点击 `button.destroy`
- 预期：列表为空；底部状态栏不可见

### TC-TODO-005 空与空白输入被拒绝
- 优先级：P0；需求：R5；自动化：`tests/test_todomvc.py::test_empty_and_whitespace_rejected`
- 数据：`""`（直接回车）、`"   "`（三个空格）
- 预期：两次操作后列表均为空

### TC-TODO-006 长度边界（1 字符 / 200 字符）
- 优先级：P2；需求：R6；自动化：`tests/test_todomvc.py::test_boundary_lengths`
- 数据：`A`；`B`×200
- 预期：两项均被接受，200 字符完整保存

### TC-TODO-007 HTML 文本转义
- 优先级：P1；需求：R7；自动化：`tests/test_todomvc.py::test_text_is_escaped`
- 数据：`<img src=x onerror=window.__xss=1>`
- 预期：条目文本与输入一致（纯文本）；`window.__xss` 为 undefined；无 alert

### TC-TODO-008（未纳入 smoke）全选与清除完成项
- 优先级：P1；需求：R8；自动化：未实现（缺口）
- 步骤：新增 3 项 → 点击 `input.toggle-all` → 点击 `button.clear-completed`
- 预期：全选后计数为 `0 items left`；Clear completed 后列表为空

### TC-TODO-009（未纳入 smoke）刷新持久化
- 优先级：P2；需求：R9；自动化：未实现（缺口）
- 步骤：新增 `Persist me` → 刷新页面
- 预期：刷新后列表仍含 `Persist me`

## 3. 需求追踪矩阵

| 需求 | 用例 | 状态 |
|---|---|---|
| R1 | TC-TODO-001 | 已自动化，RUN-CMDCHECK-03 执行 |
| R2 | TC-TODO-002 | 已自动化，未执行（smoke） |
| R3 | TC-TODO-003 | 已自动化，未执行（smoke） |
| R4 | TC-TODO-004 | 已自动化，未执行（smoke） |
| R5 | TC-TODO-005 | 已自动化，未执行（smoke） |
| R6 | TC-TODO-006 | 已自动化，未执行（smoke） |
| R7 | TC-TODO-007 | 已自动化，未执行（smoke） |
| R8 | TC-TODO-008 | 未覆盖 |
| R9 | TC-TODO-009 | 未覆盖 |

## 4. 审查记录

- 正常/异常/边界三类均已覆盖（TC-001、TC-005、TC-006）。
- 无重复用例；R1 与 R5 触发条件不同，保留。
- 未覆盖项：R8、R9 明确标注为缺口，不写成通过。
- 预期结果均为可观察状态（文本、计数、可见性、DOM 状态）。
