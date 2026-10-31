---
name: visual-testing
description: Web 截图与视觉证据：视口/整页/元素截图、截图差异计算、差异区域定位、裁剪、中文标注、热力图和证据归档。适用于 /visual-check、UI 回归复核和缺陷标注。
license: MIT
compatibility: opencode
metadata:
  audience: test-engineer
  workflow: visual
---

# visual-testing

先读 `docs/WORKFLOW.md`、`docs/CONVENTIONS.md`。截图前先确认 DOM/快照已定位，不要用截图代替元素定位。

## 截图

- 视口：`playwright-cli screenshot --filename=...`
- 整页：`playwright-cli screenshot --full-page --filename=...`
- 元素：`playwright-cli screenshot <ref> --filename=...`
- Selenium：`tests/conftest.py` 的 `CaseContext.screenshot` / 失败自动截图。
- 固定视口、缩放、语言、主题；同一对比组必须一致。
- 原始截图只增不改；裁剪/标注/差异写入 `evidence/annotated` 或 `evidence/diff`。

## 差异比较

```powershell
python tools/visual_diff.py compare `
  evidence/raw/<run>/<case>/before.png `
  evidence/raw/<run>/<case>/after.png `
  --out-dir evidence/diff/<run>/<case>-before-after `
  --label "<case-id> 前后对比" --threshold 25 --min-area 30
```

输出：

- `comparison.png`：并排对比
- `annotated.png`：差异区域框选
- `heatmap.png`：差异热力图
- `diff.png`：逐像素差异
- `mask.png`：二值掩码
- `metrics.json`：差异像素、比例、均值、RMSE、PSNR、区域
- `regions.json`：区域坐标

## 裁剪与标注

```powershell
python tools/visual_diff.py crop <image> --box x,y,w,h --out evidence/annotated/<run>/<case>/crop.png
python tools/visual_diff.py annotate <image> `
  --box "x,y,w,h,标签,#d93025" `
  --out evidence/annotated/<run>/<case>/annotated.png `
  --label "<case-id> 缺陷/变化标注"
```

- 标注图必须独立保存，原始截图不得覆盖。
- 中文标签使用系统字体；标签不遮挡关键内容，必要时调整 box 或只标区域编号。
- 裁剪图用于减少模型输入和报告体积。

## 解释规则

允许：

- 检测到视觉变化 / 未检测到超过阈值的差异；
- 差异区域位置和面积；
- 需要人工复核。

禁止仅凭像素差异：

- 判定产品缺陷；
- 判定功能失败；
- 指定严重级别。

动态内容（时间、广告、随机推荐、动画、字体渲染、滚动条）应通过固定环境或 `--ignore-box` 屏蔽后再解释。

## 证据登记

```powershell
python tools/evidence.py register --run-id <RUN_ID> --case-id <CASE_ID> `
  --kind screenshot --path evidence/raw/<run>/<case>/viewport.png --bucket raw `
  --caption "关键状态视口截图"
```

`bucket` 必须是 `raw`、`annotated`、`diff`、`logs` 之一；文件必须在对应目录下。

## 输出

- 截图清单、差异指标、区域坐标、标注图、裁剪图。
- 在报告中写“受控视觉变化/待复核”，不写未证实的缺陷。
