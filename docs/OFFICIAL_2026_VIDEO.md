# 2026 视频基线提交包（非官方认证）

- 日期：2026-10-31
- 适用：2026 全国大学生软件测试大赛 Web 应用测试赛道
- 依据：官方培训视频《2026年Web应用测试赛项介绍》与两条环境搭建视频
- 状态：**2026-video-baseline**，`official_format_confirmed=false`
- 工具：`tools/export_official_2026.py`

> 2026 官方赛题包、docx 模板、脚本包目录结构和《注意事项》尚未获取。本包只实现视频中明确展示的三项交付物和大小上限，不能声称已经通过官方 2026 格式认证。

## 1. 三项交付物

| 文件 | 格式 | 官方上限 | 本包实现 |
|---|---|---|---|
| `测试用例文档.docx` | `.docx` | 10 MB | 10 列用例表，一条用例一行 |
| `test-code.zip` | `.zip` | 10 MB | 可运行 pytest + Selenium 套件 + 官方模板参考骨架 |
| `screenshots.zip` | `.zip` | 50 MB | `screenshots/` 目录，一条用例一张 PNG |

`manifest.json` 记录 profile、大小、SHA-256、用例/截图映射和限制；`README.md` 说明包内结构和运行方式。

## 2. 生成

```powershell
python tools\export_official_2026.py `
  --run-id <RUN_ID> `
  --app <App> `
  --cases reports\test-cases\<slug>-test-cases.csv `
  --slug <slug> `
  --out official_2026
```

示例：

```powershell
python tools\export_official_2026.py `
  --run-id RUN-20261031-COLDSTART-01 `
  --app CartCheck `
  --cases reports\test-cases\cartcheck-test-cases.csv `
  --slug cartcheck `
  --out official_2026
```

产物：

```text
official_2026/<RUN_ID>/
├── 测试用例文档.docx
├── test-code.zip
├── screenshots.zip
├── screenshots/             # 解包副本，便于人工复核
├── test-code/               # 解包副本，便于人工复核
├── manifest.json
└── README.md
```

## 3. 校验

```powershell
python tools\export_official_2026.py --verify official_2026\<RUN_ID> --json
```

校验项：

- 三个交付物存在，扩展名正确；
- docx ≤10MB、脚本 zip ≤10MB、截图 zip ≤50MB；
- docx 表头为 10 列，至少一条用例，用例编号符合 `<App>_R<3位>_<3位>`；
- 截图 zip 的条目都在 `screenshots/` 下，PNG 数量与 docx 用例数一致，docx 的截图文件名都能在 zip 内找到；
- 脚本 zip 含 `pytest.ini`、`requirements.txt`、`tests/conftest.py`、`tools/evidence.py`、`tools/versioning.py` 和至少一个 `tests/generated/<slug>/test_*.py`；
- 脚本 zip 含 `official_template/Test<App>.py` 且保留 `test-code-start/end` 与官方 `take_screenshot`；
- 脚本 zip 不含 exe、本机绝对路径或本机用户名。

`verdict=PASS` 只代表“视频基线结构校验通过”；两条固定 WARNING 表示官方模板未确认、official_template 只是参考骨架。

## 4. 已实测

对 `RUN-20261031-COLDSTART-01`（CartCheck，30 条用例）实际生成并校验：

```text
profile=2026-video-baseline
case_count=30
screenshot_count=30
docx=40,356 B
test-code.zip=25,364 B
screenshots.zip=917,568 B
verify: PASS（FAIL=0，WARNING=2）
```

脚本 zip 解压到临时目录后：

```text
30 tests collected
1 passed, 29 deselected in 4.76s
```

说明它不是只能看的静态包：真的能启动 Selenium、驱动 CartCheck、执行断言。

## 5. 质量门禁 G6

`tools/pre_submission_gate.py` 已加入 G6：

```powershell
python tools\pre_submission_gate.py `
  --run-id <RUN_ID> `
  --official-2025 official_2025\<RUN_ID> `
  --official-2026 official_2026\<RUN_ID> `
  --out qualification\gate-runs\<RUN_ID>
```

- G5 继续校验 2025 官方布局；
- G6 校验 2026 视频基线三件套；
- G6 的 `OFFICIAL_TEMPLATE_UNCONFIRMED` 和 `SCRIPT_REFERENCE_ONLY` 是 WARNING，不会把本地演练判成 FAIL；
- `--official-submission` 下，合规项仍应按未确认处理，不能因为 G6 PASS 就声称官方 2026 合规。

## 6. 与官方 2026 的差距

| 项 | 当前 | 官方包到手后 |
|---|---|---|
| docx 模板 | 自定义 10 列表格 | 按官方模板替换样式/字段顺序 |
| 脚本包结构 | pytest 套件 + 参考骨架 | 按官方模板替换入口、函数命名、依赖 |
| 截图命名 | 沿用 2025 `<11位时间戳>_<编号>.png` | 按 2026《注意事项》确认 |
| 用例编号 | 沿用 `<App>_R<3位>_<3位>` | 按 2026 模板确认 |
| 官方认证 | `official_format_confirmed=false` | 官方模板校验通过后才可改 true |

## 7. 相关文件

- `tools/export_official_2026.py`：生成与校验
- `tools/pre_submission_gate.py`：G6
- `official_2026/RUN-20261031-COLDSTART-01/`：本次样例
- `docs/COMPETITION_RULES_2026.md`：视频规则来源
- `docs/ISOLATION_PROTOCOL.md`：实测答案隔离
