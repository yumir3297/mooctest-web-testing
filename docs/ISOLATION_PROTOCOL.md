# 实测题目与答案隔离协议

- 用途：第一次实测/限时演练前，防止被测 agent 在跑测试时看到参考答案、历史报告或同一目标的先前产物。
- 结论：**要隔离，而且不能只在当前工作区里改名或挪子目录**。跑测试的 agent 有当前用户的全盘读权限，正确做法是另建干净工作区，把答案放到工作区外。

## 1. 哪些东西算“答案”

| 类别 | 当前路径 | 处理 |
|---|---|---|
| 官方参考答案 | `materials/参考答案/` | 移出干净工作区 |
| 原始参考答案压缩包 | `materials/_原始压缩包/` | 移出干净工作区 |
| 本地练习应用的实现源码 | `fixtures/cartcheck/app.js` 等 | 不放进干净工作区；应用单独启动 |
| 同一目标的先前测试用例 | `reports/test-cases/` | 移出干净工作区 |
| 同一目标的先前截图/日志 | `evidence/` | 移出干净工作区 |
| 同一目标的先前报告 | `reports/executions/` | 移出干净工作区 |
| 官方格式导出与交付包 | `official_2025/`、`submission/` | 移出干净工作区 |
| 先前生成的测试代码 | `tests/generated/` | 移出干净工作区 |
| 规则/课程知识库 | `knowledge/` | 干净工作区只保留 `.opencode/skills/` 的方法论 |
| 公开发布快照 | `publish/` | 移出干净工作区；实测时不要打开 GitHub 仓库 |
| 电子书/第三方资料 | `booook/` | 移出干净工作区 |

题干本身（需求文档、功能说明手册、注意事项、用例模板、官方代码模板）**可以**放进干净工作区；`materials/参考答案` 不行。

## 2. 推荐布局

```text
C:\TempPG\mooctest-exam-<日期>\
├── workspace\                 # 被测 agent 的工作目录
│   ├── AGENTS.md
│   ├── README.md
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── opencode.json
│   ├── docs\                  # 只放流程/规范/2026 规则
│   ├── tools\                 # 流水线、证据、报告、门禁
│   ├── tests\                 # 只保留 TodoMVC 基线 + conftest
│   ├── templates\
│   ├── .opencode\skills\      # 方法论 Skill
│   ├── .agents\skills\        # 外部 Skill（可选）
│   └── materials\             # 只放本题题干，不放参考答案
└── target\                    # 本地被测应用（可选，放在 workspace 外）

C:\TempPG\mooctest-answer-vault\   # 参考答案/历史报告，实测期间不放进 workspace
```

如果测的是远程比赛站点，`target\` 不需要，干净工作区里只保留题干和 harness。

## 3. 干净工作区的最小内容

**保留**

- `AGENTS.md`、`README.md`、`requirements.txt`、`pytest.ini`、`opencode.json`
- `docs/WORKFLOW.md`、`docs/CONTRACTS.md`、`docs/CONVENTIONS.md`、`docs/REPORTING.md`
- `docs/COMPETITION_RULES_2026.md`、`docs/ENVIRONMENT.md`
- `tools/`（含 `tools/driver/` 的固定驱动；不要带 `tools/driver/archive`）
- `tests/conftest.py`、`tests/pages/todo_page.py`、`tests/test_todomvc*.py`
- `templates/`
- `.opencode/skills/`、`.opencode/commands/`
- `.agents/skills/`（可选）

**不要保留**

- `materials/参考答案/`、`materials/_原始压缩包/`
- `reports/`、`evidence/`、`pipeline_runs/`、`qualification/`
- `official_2025/`、`submission/`
- `tests/generated/`
- `fixtures/`（如果它是本题被测应用的源码）
- `knowledge/`、`publish/`、`booook/`、`backups/`
- `node_modules/` 可以复制或做 junction，但它不是答案；如果做 junction，注意不要顺带暴露原工作区其他目录

## 4. 开跑前门禁

在干净工作区根目录执行：

```powershell
python tools\isolation_check.py --workspace . --json
```

- `verdict=ISOLATION_CLEAN`、退出码 0 → 可以开始。
- `verdict=ISOLATION_CONTAMINATED`、退出码 2 → 按输出清单把答案源移出干净工作区，再重跑。

脚本检查的是已知答案路径和 `materials/` 下的答案文件名；它是**开跑前**门禁。测试跑完后 `reports/`、`evidence/`、`tests/generated/` 会出现，属于正常产物，不要再用它判定污染。

## 5. 本地练习应用的特殊处理

如果被测目标是 `fixtures/cartcheck`：

1. 把 `fixtures/cartcheck/` 复制到 `C:\TempPG\mooctest-exam-<日期>\target\cartcheck\`（workspace 外）。
2. 在 `target\cartcheck\` 启动 `python serve.py --port 8765`。
3. 干净工作区只放 `REQUIREMENTS.md`（题干）和 target URL，**不要放 `app.js`**。
4. 被测 agent 只通过浏览器访问 `http://127.0.0.1:8765/`，看不到实现源码。

注意：`REQUIREMENTS.md` 里的计算示例（E1–E7）是需求的一部分，不是参考答案；可以保留。真正的答案（实现源码、参考截图、历史用例）不要放进 workspace。

## 6. 隔离强度的边界

这是**软隔离**：它防的是“agent 在干净工作区里顺手读到答案”，不是“同一 Windows 用户恶意翻盘”。

- 同一用户仍然可以读 `C:\TempPG\mooctest-answer-vault\`，只是干净工作区里没有路径提示。
- 要更强隔离，需要：
  - 用另一个 Windows 用户运行被测 agent，并对答案目录做 ACL 拒绝；或
  - 把答案放进加密容器，密码不进入 agent 上下文；或
  - 把答案放在另一台机器/未挂载的云盘。
- 对比赛演练，软隔离 + 干净工作区 + 不开 GitHub 仓库通常足够；不要把“软隔离”说成“安全隔离”。

## 7. 实测结束后的对照

1. 人工在 `mooctest-answer-vault` 打开参考答案/参考截图。
2. 对照 `reports/executions/<RUN>/` 和 `evidence/raw/<RUN>/`。
3. 不要把参考答案内容粘贴回被测 agent 的会话；如需复盘，另开一个“复盘会话”，明确它可以看到答案。

## 8. 相关命令

```powershell
# 隔离检查
python tools\isolation_check.py --workspace . --json

# 环境门禁
python tools\env_check.py --strict

# 实测入口
/web-test target=<URL> requirement=<题干路径> slug=<slug> scope=full
```
