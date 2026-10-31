# 命名、目录与证据约定

## 1. 目录

```text
evidence/
├── raw/<run_id>/<case_id>/      原始截图、快照、页面源码
├── annotated/<run_id>/<case_id>/ 裁剪图、人工标注图
├── diff/<run_id>/<case_id>/     差异图、热力图、指标、区域
├── logs/<run_id>/               执行日志、控制台日志
└── manifest.json                唯一证据索引

reports/
├── test-cases/                  需求分析、用例设计、审查
├── executions/<run_id>/         JUnit、报告、执行摘要
└── defects/                     缺陷清单
```

## 2. ID

- 运行：`RUN-YYYYMMDD-HHMMSS`，例如 `RUN-20261029-02`。
- 用例：`TC-<模块>-<三位序号>`，例如 `TC-TODO-001`。
- 缺陷：`DEF-<三位序号>`，由 `tools/evidence.py add-defect` 生成。
- 证据：`EV-<10 位哈希>`，由证据管理器生成。

## 3. 文件名

格式：

```text
<case_id>__<stage>__<kind>__<UTC时间戳>.<ext>
```

示例：

```text
TC-TODO-001__failure__viewport__20261029T092216-142.png
TC-TODO-001__final__fullpage__20261029T092211-218.png
TC-TODO-099__failure__page-source__20261029T092216-142.html
```

- 时间戳统一 UTC，避免本地时区歧义。
- 不使用空格、中文文件名；中文只放在 manifest 的 `caption` 和报告中。
- 原始证据只增不改；修正版另存到 `annotated/` 或 `diff/`。

## 4. Manifest 字段

每条证据至少包含：

- `evidence_id`
- `run_id`
- `case_id`
- `kind`（screenshot / fullpage-screenshot / element-screenshot / snapshot / page-source / log / diff / heatmap / annotation / comparison / crop / metrics / regions）
- `path`（相对项目根目录）
- `bucket`（raw / annotated / diff / logs）
- `created_at`
- `size_bytes`
- `sha256`
- `width` / `height`（图片）
- `caption` / `step`
- `immutable`

用例至少包含：

- `case_id`
- `title`
- `status`
- `expected`
- `actual`
- `steps`
- `assertions`
- `evidence`（evidence_id 列表）
- `log_path`
- `defects`

## 5. 截图策略

- 视口固定 1280×720 或 1280×900；同一对比组必须一致。
- 字体、主题、语言、缩放一致。
- 元素截图优先；整页截图用于布局/遮挡/溢出。
- 失败时默认保存视口 + 整页 + 页面源码 + 浏览器日志。
- 不截图登录凭据、支付信息、个人隐私；必要时打码并保留打码说明。

## 6. 视觉差异解释

允许的结论：

- “检测到受控视觉变化”
- “差异区域位于 …”
- “需要人工复核”
- “未检测到超过阈值的像素差异”

不允许仅凭像素差异写：

- “存在 UI 缺陷”
- “功能失败”
- “严重级别为 …”

要登记缺陷，必须有可复现步骤、预期/实际行为、DOM/日志证据，并在报告中写明复现环境。

## 7. 日志

- 运行日志：`evidence/logs/<run_id>/pytest.log`
- 控制台日志：`evidence/logs/<run_id>/pytest-console.log`
- 用例日志：`evidence/logs/<run_id>/<case_id>.log`
- 浏览器控制台：`evidence/logs/<run_id>/<case_id>__browser__<timestamp>.log`

日志中不得写入密码、令牌、Cookie 值。需要记录时使用 `<masked>`。

## 8. 报告门禁

- 没有 JUnit 或 manifest 的执行结果，不写“通过”。
- 没有证据的用例，报告中标注“证据不完整”。
- `xfailed` 单独统计，不计入通过率。
- 每个失败用例必须能链接到截图、页面源码或日志。
- 报告生成后运行 `python tools/evidence.py verify --run-id <run_id> --fail-on-error`。
