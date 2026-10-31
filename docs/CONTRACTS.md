# 模块接口契约（集成前冻结）

本文件定义各模块之间的机器可读契约。实现必须遵守；如确需变更，由主 Agent 统一修改本文件并通知所有模块。

## 1. Manifest（`evidence/manifest.json`）v1.1

由 `tools/evidence.py` 独占写入。关键结构：

```jsonc
{
  "schema_version": "1.1",
  "runs": {
    "RUN-X": {
      "run_id": "RUN-X", "target": "…", "status": "running|passed|failed|blocked|aborted",
      "stage": "…", "started_at": "…", "finished_at": "…",
      "environment": {"python":"…","selenium":"…","pytest":"…","chrome":"…","chromedriver":"…","target":"…"},
      "notes": [{"at":"…","note":"…"}],
      "cases": {
        "TC-X-001": {
          "case_id": "TC-X-001", "title": "…", "status": "passed|failed|xfailed|blocked|skipped|not-run|running",
          "expected": "用例级预期（只由 set_expected 写入）",
          "actual": "用例级实际（失败时由 hook 写入）",
          "steps": ["…"], "assertions": [{"name":"…","expected":"…","actual":"…","passed":true}],
          "evidence": ["EV-…"], "defects": [ /* 见 §1.1 */ ],
          "log_path": "evidence/logs/RUN-X/TC-X-001.log",
          "meta": {"requirement_ids":"REQ-01","method":"BVA","priority":"P0","case_type":"boundary","failure_class":"ASSERT"},
          "duration_ms": 1234
        }
      }
    }
  },
  "evidence": [
    {"evidence_id":"EV-…","run_id":"RUN-X","case_id":"TC-X-001","kind":"screenshot","path":"evidence/raw/RUN-X/TC-X-001/…png",
     "bucket":"raw","sha256":"…","size_bytes":123,"immutable":true,"meta":{},"width":1280,"height":900}
  ]
}
```

### 1.1 缺陷对象

```jsonc
{
  "defect_id": "DEF-001", "title": "…",
  "severity": "blocker|critical|major|minor|trivial",
  "severity_rationale": "…", "category": "APP|SCRIPT|ENV|DATA|LOCATOR|TIMING|UNKNOWN",
  "status": "open|confirmed|suspected|needs_review|not_a_defect|fixed",
  "description": "…", "environment": "…",
  "preconditions": ["…"], "repro_steps": ["…"],
  "repro_status": "not-reproduced|reproduced|intermittent|blocked", "repro_count": 2,
  "expected": "…", "actual": "…", "evidence": ["EV-…"], "created_at": "…"
}
```

### 1.2 硬约束（由 `evidence.py` 强制执行）

- `register_evidence`：路径必须在 `evidence/<bucket>/` 下；路径中出现 `RUN-*` 且与 `run_id` 不一致 → 拒绝；同一 run 同一路径重复登记 → 拒绝。
- `update_case(status="passed")`：该用例必须有 `assertions` 或 `evidence`，否则拒绝。
- `add_defect`：严重度、状态、分类必须取自枚举。

## 2. JUnit 摘要（`reports/executions/<run>/junit-summary.json`）

由 `tools/run_selenium.py` 写入：

```jsonc
{"run_id":"RUN-X","exit_code":0,"elapsed_seconds":12.3,"timed_out":false,
 "junit":"…junit.xml","console_log":"…pytest-console.log",
 "tests":8,"failures":0,"errors":0,"skipped":0,"xfailed":1,
 "cases":[{"name":"test_add_todo","classname":"tests.test_todomvc","time":1.2,"status":"passed|failed|xfailed|skipped","message":""}],
 "status":"passed|failed|blocked"}
```

## 3. 用例表（`reports/test-cases/<slug>-test-cases.csv`，UTF-8 BOM）

规范列（顺序固定）：

```text
case_id,title,priority,requirement_ids,case_type,method,preconditions,test_data,steps,expected,actual,status,automation,evidence_required,executed_in_run,notes
```

- `case_type ∈ {positive, negative, boundary, state, combination, nonfunctional}`
- `priority ∈ {P0,P1,P2,P3}`
- `automation`：`<file>::<test_func>` 或空（手工/未实现）
- 兼容别名（读取时映射）：`requirement→requirement_ids`、`precondition→preconditions`、`data→test_data`、`evidence→evidence_required`

Markdown 用例文档可选，但 CSV 是门禁的唯一机器输入。

## 4. 质量门禁 CLI（`tools/pre_submission_gate.py`）

```text
python tools/pre_submission_gate.py --run-id RUN-X [--cases PATH] [--junit-summary PATH]
       [--manifest PATH] [--submission PATH] [--out DIR] [--gates G0,G1,G2,G3,G4] [--json]
```

输出：`<out>/gate-report.json`（默认 `<out>` = `qualification/gate-runs/<run_id>/`）。

```jsonc
{"schema_version":"1.0","run_id":"RUN-X","generated_at":"…",
 "gate_status":{"G0":"PASS","G1":"PASS","G2":"FAIL","G3":"WARNING","G4":"SKIP"},
 "delivery_verdict":"PASS|WARNING|FAIL|BLOCKED|UNVERIFIED",
 "test_verdict":"PASS|FAIL|BLOCKED|UNVERIFIED",
 "findings":[{"gate":"G2","code":"CASE_WITHOUT_ASSERTION","severity":"FAIL","subject":"TC-X-001","message":"…","evidence":"…"}],
 "summary":{"FAIL":1,"WARNING":2,"BLOCKED":0,"UNVERIFIED":0,"PASS":30}}
```

**核心区分**：`test_verdict` 回答「被测应用是否通过测试」；`delivery_verdict` 回答「这批测试成果是否可信、可交付」。真实产品缺陷导致 `test_verdict=FAIL`，只要缺陷已确认并取证，`delivery_verdict` 仍可为 `PASS`。

退出码：`0` PASS/WARNING，`1` FAIL，`2` BLOCKED，`3` UNVERIFIED。

### 4.1 门禁清单

| Gate | 内容 | 失败示例 |
|---|---|---|
| G0 | 环境与合规 | 缺 chrome/chromedriver 版本；主版本不一致；`AI_USE_CONFIRMED` 未声明 → UNVERIFIED（不阻断本地演练，阻断正式提交声明） |
| G1 | 需求与用例 | 空用例集；缺 expected；重复 case_id；缺 requirement_ids；缺 positive/negative/boundary |
| G2 | 脚本与执行 | 语法错误；pytest 收集失败；case_id 无对应测试函数；无断言；`time.sleep`；JUnit 与 manifest 计数矛盾；缺 JUnit |
| G3 | 缺陷与证据 | manifest 缺失/哈希不一致/跨 run；passed 用例无证据；failed 用例既无缺陷也无失败分类；缺陷缺复现步骤/严重度依据 |
| G4 | 交付包 | 缺 xlsx/zip；哈希不符；用例与代码/截图关联缺失（仅在提供 `--submission` 时执行，否则 `SKIP`） |

## 5. 交付包（`submission/<RUN-X>/`）

```text
submission/RUN-X/
  test-cases.xlsx
  test-code/
  screenshots/
  reports/
  manifest.json
  submission.zip
```

`tools/package_submission.py` 生成，`--verify` 校验。`manifest.json` 逐文件记录 `path/sha256/size/case_id/source`。zip 内条目时间戳固定，重复生成应字节一致（除 `generated_at` 字段外）。

## 6. 流水线状态（`pipeline_runs/<RUN-X>/state.json`）

```jsonc
{"schema_version":"1.0","run_id":"RUN-X","target":"…","requirement":"…","scope":"smoke|full",
 "current_stage":"TEST_DESIGN","stages":[{"name":"INIT","status":"done","started_at":"…","finished_at":"…","note":"…","artifacts":["…"]}],
 "artifacts":{},"revision":3}
```

阶段顺序固定：

```text
INIT → ENV_CHECK → KNOWLEDGE_LOAD → REQUIREMENT_ANALYSIS → BROWSER_EXPLORATION →
TEST_DESIGN → CASE_REVIEW → SCRIPT_GENERATION → SCRIPT_VALIDATION → TEST_EXECUTION →
FAILURE_TRIAGE → EVIDENCE_REVIEW → COVERAGE_REVIEW → REPORT_GENERATION → QUALITY_GATE →
PACKAGE_PREPARATION → COMPLETE
```

每个阶段声明必须产物；`advance` 校验产物存在才推进，否则非零退出。
