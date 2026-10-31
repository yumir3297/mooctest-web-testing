# 报告与交付包（reporting & packaging）

本文件说明 `tools/generate_report.py`（报告）与 `tools/package_submission.py`（交付包）的字段、门禁与限制。
机器可读契约以 `docs/CONTRACTS.md` 为准；本文件解释实现口径。

## 1. 入口

```text
python tools/generate_report.py --run-id RUN-X [--title T] [--out-dir DIR]
       [--cases PATH] [--junit-summary PATH] [--require-cases N]
       [--gate | --no-gate] [--no-env-probe] [--json]
       [--manifest PATH] [--project-root DIR] [--reports-root DIR]

python tools/package_submission.py --run-id RUN-X [--cases PATH] [--report-dir PATH]
       [--out submission] [--json] [--force-reports]
python tools/package_submission.py --verify submission/RUN-X [--json]
```

默认输出目录仍为 `reports/executions/<run>/`。工具只写 `--out-dir`（报告）与 `--out`（交付包）；
`reports/defects/` 不再被隐式写入，缺陷清单写在报告的 `defects.md`。

## 2. 报告结构

Markdown 与 HTML 同步包含 12 节；`report.json`（schema 2.0）是它们的结构化来源。

| 节 | 内容 | `report.json` 键 |
|---|---|---|
| 1 | 测试目标与范围（target / scope / 需求来源 / 用例表） | `scope`, `summary` |
| 2 | 测试环境（9 个固定字段 + 来源 + 报告生成时探测） | `environment`, `environment_meta`, `environment_probe` |
| 3 | 测试策略与设计方法（按用例表 `method` 聚合） | `strategy` |
| 4 | 用例与执行结果表 | `cases`, `summary` |
| 5 | 用例明细（前置条件/数据/步骤/用例级预期与实际/断言/证据/缺陷） | `cases` |
| 6 | 缺陷（完整字段 + 复现步骤 + 证据） | `defects` |
| 7 | 视觉差异（像素差异仅作复核信号） | `visual` |
| 8 | 证据完整性（checked/ok/missing/mismatched/cross_run/unscoped/duplicates） | `evidence` |
| 9 | 执行日志（JUnit、控制台、统计） | `junit`, `junit_counts`, `test_functions` |
| 10 | 需求覆盖情况（有/无用例、未执行需求、未关联需求的用例） | `coverage` |
| 11 | 未执行项与已知限制 | `coverage`, `limitations` |
| 12 | 质量门禁结果（内联 `gate-report.json` + 本报告门禁） | `quality_gate`, `gate` |

### 2.1 用例级预期与实际

- `case.expected` / `case.actual` 只由 `CaseContext.set_expected()` / `set_actual()` 写入（`tests/conftest.py`）。
- 历史运行里被断言布尔值污染的值（`True` / `False` / `None`）**不会**作为用例预期展示：
  `expected` 置空，`expected_source="assertions"`，`expected_invalid=true`，`expected_raw` 保留原值，
  报告显示「见断言明细（N 条断言）」并附一行说明。
- 断言布尔值只出现在断言表（第 5 节），不会回填到用例级字段。
- `expected_source` 取值：`case`（运行记录写入）、`assertions`（回退到断言明细）、`missing`（两者皆无）。

### 2.2 测试环境

固定 9 个字段，缺失时显示「未采集」而不是省略：`os, platform, python, selenium, pytest, chrome, chromedriver, node, target`。
运行记录里的占位符（`<empty>` / `<not found>` / `<import failed: …>`）显示为「未采集（运行记录为 …）」。

报告生成时的本机探测单独放在「环境补充探测」小节，带 `probe_kind=report-time` 与显式声明：
**探测值不覆盖运行记录**。Chrome 版本读取 PE 版本资源，不执行 `chrome.exe --version`
（该命令在 Windows 上不输出且可能弹窗）。

### 2.3 用例表必须是本运行的

`_case_rows()` 旧实现会在找不到本运行用例表时回退到 `todomvc-test-cases.csv`，把别的运行的
未执行用例算成本运行的覆盖缺口。现在：

- 只在 `reports/test-cases/*.csv` 中查找 `executed_in_run` **按 run id token 精确匹配**（`RUN-X` 不匹配 `RUN-X2`）的表；
- 找不到就输出「未找到本运行的用例表（没有 CSV 的 executed_in_run 包含 RUN-X）」，
  `strategy.methods=[]`、需求覆盖只依据 manifest 的 `meta.requirement_ids`；
- 需要人工指定时用 `--cases PATH`，此时 `case_table.source="explicit"`。

### 2.4 统计口径

- 通过率 = `passed / (passed + failed)`；`xfailed`、`skipped`、`not-run` 不计入分母。
- `xfailed` 单独统计，不计入通过率，也不等同于产品缺陷。
- JUnit 计数与 manifest 计数并列展示，不做合并或换算。

## 3. 报告交付门禁（`--gate`，默认开启）

退出码：`0` PASS/WARNING，`1` FAIL，`2` BLOCKED。

| 级别 | 代码 | 触发条件 |
|---|---|---|
| BLOCKED | `RUN_NOT_EXECUTED` | 运行状态为 `blocked` / `aborted` |
| BLOCKED | `NO_CASES` | manifest 未登记任何用例 |
| FAIL | `NO_EXECUTED_CASES` | 有用例但全部未执行/阻塞 |
| FAIL | `JUNIT_MISSING` / `JUNIT_XML_MISSING` | 缺 `junit-summary.json` 或缺 JUnit 文件 |
| FAIL | `CASE_EXPECTED_MISSING` | 用例无预期且无断言明细 |
| FAIL | `MANIFEST_EVIDENCE_MISSING` / `MANIFEST_HASH_MISMATCH` | 证据缺失或哈希不符 |
| FAIL | `REQUIRE_CASES_SHORTFALL` | 用例数少于 `--require-cases` |
| WARNING | `CASE_EXPECTED_FROM_ASSERTIONS` | 用例级预期缺失/被历史断言值污染，已回退断言明细 |
| WARNING | `CASE_TABLE_MISSING` | 未找到本运行的用例表 |
| WARNING | `PASSED_CASE_WITHOUT_EVIDENCE` | 通过用例无证据 |
| WARNING | `CASE_NOT_IN_CASE_TABLE` | 用例不在本运行用例表（仅当表存在） |
| WARNING | `EVIDENCE_CROSS_RUN` / `EVIDENCE_UNSCOPED` | 证据路径跨 run / 无 run id |
| WARNING | `QUALITY_GATE_NOT_RUN` | 无 `qualification/gate-runs/<run>/gate-report.json` |

`--no-gate` 关闭门禁（`verdict=DISABLED`），此时退出码沿用旧行为：证据缺失/哈希不符退出 1。

## 4. 交付包

```text
submission/RUN-X/
  test-cases.xlsx          契约 §3 的 16 列；首行加粗冻结、列宽自适应、status 条件着色
  test-code/               tests/conftest.py、tests/pages/**、被 automation 引用的测试文件、pytest.ini、requirements.txt
  screenshots/             本运行全部图片证据（文件名保持原样）+ index.csv
  reports/                 report.md/html/json、junit.xml、junit-summary.json、pytest-console.log
  README.md                内部演练声明
  manifest.json            schema 1.0，逐文件 path/sha256/size_bytes/case_id/source
  submission.zip           稳定 zip
```

- **官方格式**：`manifest.json` 与 `--json` 输出都固定 `official_format_confirmed: false`，
  README 写「内部演练交付包，2026 官方提交格式未确认」。本工具不声称符合任何官方格式。
- **用例表来源**：`run-scoped`（本运行 CSV）→ `explicit`（`--cases`）→
  `synthesised-from-manifest`（没有 CSV 时由 manifest 合成，xlsx 的 `notes` 标注来源）。
- **报告文件**：包内 `reports/` 已有报告时保留（不覆盖），缺失时依次从 `--report-dir`、
  `reports/executions/<run>/` 复制；`--force-reports` 强制覆盖。JUnit 与 console log 依据
  `junit-summary.json` 中的路径定位。
- **稳定 zip**：条目按路径排序，`date_time` 固定 `(1980,1,1,0,0,0)`，`ZIP_DEFLATED`，
  `create_system=0`。xlsx 内部 `docProps/core.xml` 的时间戳与 zip 条目时间同样被钉死；
  `generated_at` 只写在 `manifest.json`（不在 zip 内）。因此同一运行重复打包的 zip 字节一致。
- **`--verify` 校验**：目录/文件齐全；每个文件的大小与 sha256；zip 可解压且解压后哈希一致、
  条目有序；xlsx 可打开、表头等于契约列、数据行数等于 `case_count`、无重复 `case_id`；
  每条用例关联到已复制的测试文件且函数存在，否则必须标注「未实现」；每个 `passed` 用例至少 1 张截图。
  失败退出 1。

## 5. 已知限制与内部约定

- 「官方提交格式未确认」：目录名、文件名、xlsx 列定义、`manifest.json` 字段均为本项目内部约定。
- 报告内的图片链接指向项目树（`evidence/…`），因此单独拷出 `reports/` 时图片会失效；
  包内独立截图见 `screenshots/` 与 `index.csv`。
- 环境探测值来自报告生成机器，可能与运行机器不同，报告中已分栏标注。
- `case.expected` 的合法性无法从历史数据完全还原：`True`/`False`/`None` 之外的历史断言取值
  （如列表快照）仍会按原值展示，报告中不做二次推断。
- 缺陷 `suspected` / `needs_review` 一律显式标注「疑似/待复核，未确认为产品缺陷」。
- 像素差异只作为复核信号，不单独构成缺陷结论。

## 6. 自测

```text
python -m pytest tests_meta_report -q
```

覆盖：真实运行报告（用例级预期不回填断言布尔值、环境含 chrome/chromedriver）、
本运行用例表缺失的显式声明、显式用例表的 method/需求聚合、缺 JUnit 的门禁失败、
0 用例的 BLOCKED、`--no-gate` 兼容、打包两次 zip 字节一致、`--verify` 通过、
`official_format_confirmed=false`。
