# 探索记录：TodoMVC（RUN-CMDCHECK-03）

## 页面清单

| 项 | 值 |
|---|---|
| URL | https://demo.playwright.dev/todomvc（应用内路由 `#/`、`#/active`、`#/completed`） |
| 标题 | React • TodoMVC |
| 视口 | 1280×720 |
| 初始状态 | 仅输入框 `What needs to be done?`，无列表、无 footer |

## 稳定选择器（已用真实 DOM 验证）

| 元素 | 选择器 | 验证方式 |
|---|---|---|
| 新增输入框 | `input.new-todo`（role=textbox, name="What needs to be done?"） | 快照 ref=e8 + 实际输入回车成功 |
| 列表项 | `.todo-list li` | 新增后快照出现 listitem |
| 条目标题 | `label[data-testid='todo-title']` | page.getByTestId('todo-item') 命中 |
| 完成勾选 | `input.toggle`（checkbox "Toggle Todo"） | 快照 ref=e21 |
| 全选 | `input.toggle-all` | 快照 ref=e16 |
| 删除 | `button.destroy` | 条目内 × 按钮 |
| 计数 | `span.todo-count` | 新增后为 "1 item left" |
| 状态栏 | `footer.footer` | 有数据时出现，空列表时不存在 |
| 过滤器 | `ul.filters a[href='#/']`、`#/active`、`#/completed` | 快照 link 结构 |
| 清除已完成 | `button.clear-completed` | 需存在已完成项时出现 |

## 交互路径（已验证）

1. 打开页面 → 输入框可见。
2. 输入 `Buy milk` + Enter → `.todo-list li` 数量 1，`span.todo-count` 文本 `1 item left`，`footer.footer` 可见。

## 控制台 / 网络

- 仅有 1 条错误：`GET https://demo.playwright.dev/favicon.ico` 返回 404。属静态资源缺失，不影响功能，未登记为业务缺陷。
- 无 JavaScript 运行时异常，无失败 XHR。

## 风险与注意事项

- 列表为空时 `footer.footer` 与 `span.todo-count` 不存在，断言必须用“元素不存在”而不是“不可见”。
- React 渲染为异步，读取列表数量必须显式等待计数变化。
- 状态保存在 localStorage，用例间需清理以避免污染。
- 删除按钮悬停才可见，需 `ActionChains.move_to_element`。

## 未覆盖路径

- Toggle all + Clear completed（TC-TODO-008，未实现自动化）。
- 刷新持久化（TC-TODO-009，未实现自动化）。
- 移动端/响应式布局与键盘可访问性未验证。

## 证据

| evidence_id | 内容 |
|---|---|
| EV-9bad8c36f8 | 新增后无障碍快照 |
| EV-9951668576 | 待办条目元素截图 |
| EV-ce9c86ee17 | 新增后视口截图 |
| EV-047203b000 | 浏览器控制台日志 |
