# 2026 视频基线测试脚本包

- 运行入口：`tests/generated/cartcheck/test_*.py`（pytest + Selenium）。
- 运行方式：

  ```powershell
  pip install -r requirements.txt
  pytest --target <被测站点 URL>
  ```

- `official_template/TestCartCheck.py` 是官方模板结构的参考骨架，保留
  `test-code-start` / `test-code-end`，但函数体未实现；2026 官方模板未获取。
- 本地调试时用 `MOOCTEST_CHROMEDRIVER` 指向本机驱动；提交到官方环境前，
  按模板要求使用官方驱动路径。
- 本包由 `tools/export_official_2026.py` 生成，profile=`2026-video-baseline`，
  不代表官方 2026 格式已确认。
