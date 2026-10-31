# 测试授权记录

- 目标：`http://127.0.0.1:8765/`（CartCheck 结算试算器，本地自建练习应用）
- 授权来源：本地自建 fixture，仅监听 127.0.0.1，无外部网络访问
- 允许：输入任意测试数据、截图、写入本项目测试与证据目录
- 禁止：修改被测实现、访问外网、绕过认证（本应用无认证）
- 声明：本次为内部演练，`AI_USE_CONFIRMED` 未声明，不用于正式比赛提交

注：`tools/pipeline.py init` 当前版本不接受 `--authorized` 参数（argparse 报
`unrecognized arguments: --authorized`），因此授权说明以本文件落盘，
并作为 run 级产物保留。
