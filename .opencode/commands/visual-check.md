---
description: 视觉检查：截图、差异、裁剪、标注并登记证据
agent: build
---

目标：$ARGUMENTS

先加载 `visual-testing` Skill，并读取 `docs/WORKFLOW.md`、`docs/CONVENTIONS.md`。

## 参数约定

- `target=<URL>`：需要打开的页面。
- `baseline=<path>`、`actual=<path>`：已有截图对比。
- `case_id=<TC-...>`、`run_id=<RUN-...>`：证据关联；缺省时生成或使用最近运行。
- `--full-page`、`--element=<selector>`：截图范围。
- `--check`：只检查环境，不启动浏览器。

## 步骤

1. 若参数含 `--check`：检查 Python、Pillow、OpenCV、`tools/visual_diff.py`、`tools/evidence.py` 可用，输出 `VISUAL_CHECK_READY`，停止。
2. 若提供 `target`：
   - 优先用当前可用的 Playwright MCP `browser_*` 工具；不可用时用 `npx --no-install playwright-cli -s=<session>`。
   - 先 `snapshot` 定位，再截图；保存到 `evidence/raw/<run>/<case>/`。
   - 视口/整页/元素截图分别命名；不要把图片直接塞进上下文，只引用路径。
3. 若提供 `baseline`/`actual`：
   - 运行 `python tools/visual_diff.py compare ... --out-dir evidence/diff/<run>/<case> --label "<case>"`。
   - 读取 `metrics.json`、`regions.json`；生成裁剪/标注图时写入 `evidence/annotated/<run>/<case>/`。
4. 用 `python tools/evidence.py register` 登记每份证据（bucket 必须匹配目录）。
5. 输出：证据路径、图片尺寸、差异像素/比例、区域坐标、结论。结论只能写“受控变化/待复核/未检测到超阈值差异”，不能仅凭像素差异写产品缺陷。
