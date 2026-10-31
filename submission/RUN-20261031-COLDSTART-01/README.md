# RUN-20261031-COLDSTART-01 测试交付包

**内部演练交付包，2026 官方提交格式未确认。**

本目录由 `tools/package_submission.py` 生成，用于内部演练与交叉复核，不声明符合任何官方提交格式（`official_format_confirmed: false`）。

## 目录

- `test-cases.xlsx`：用例表（sheet `test-cases` 为契约列；sheet `run-info` 为运行信息）
- `test-code/`：执行本批用例所需的最小代码（conftest、页面对象、被引用测试文件、pytest.ini、requirements.txt）
- `screenshots/`：本运行登记的全部图片证据，`index.csv` 记录 case_id/evidence_id/kind/文件/sha256/说明
- `reports/`：report.md、report.html、report.json、junit.xml、junit-summary.json、pytest-console.log
- `manifest.json`：逐文件 sha256 与大小（schema 1.0）
- `submission.zip`：上述载荷的稳定压缩包（条目排序、时间戳固定 1980-01-01）

## 运行信息

- 目标：http://127.0.0.1:8765/
- 用例数：30
- 用例表来源：run-scoped

## 校验

```text
python tools/package_submission.py --verify submission/RUN-20261031-COLDSTART-01 --json
```

## 限制

- 官方提交格式未确认；目录名、文件命名与 xlsx 列定义均为本项目内部约定。
- 报告中的图片链接指向项目树（`evidence/…`）；包内独立截图见 `screenshots/`。
- zip 只包含载荷文件，`manifest.json` 与 `submission.zip` 同级存放，压缩包内不含二者。
