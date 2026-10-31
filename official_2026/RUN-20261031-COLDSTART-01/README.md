# 2026 视频基线提交包（RUN-20261031-COLDSTART-01）

依据 2026 官方培训视频整理，**不是已确认的官方 2026 模板**。

## 三项交付物

| 文件 | 格式 | 大小上限 | 本包大小 |
|---|---|---|---|
| 测试用例文档 | `.docx` | 10 MB | 40356 B |
| 测试脚本压缩包 | `.zip` | 10 MB | 25364 B |
| 测试截图压缩包 | `.zip` | 50 MB | 917568 B |

- 用例：30 条，10 列；截图：30 张，一条用例一张。
- 脚本 zip 的运行入口是 `tests/generated/cartcheck/test_*.py`；`official_template/TestCartCheck.py`
  是保留 markers 的参考骨架。
- 截图来自 `evidence/` 中的真实运行，未重绘、未伪造。

## 边界

- 2026 官方 docx 模板、脚本包目录结构、赛题包《注意事项》尚未获取。
- 本包 profile=`2026-video-baseline`、`official_format_confirmed=false`；不能声称官方 2026 合规。
- 缺截图的用例：无。

生成时间：2026-10-31T21:38:18+08:00
