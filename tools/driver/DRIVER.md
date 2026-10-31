# ChromeDriver 版本记录

本文件是 `tools/driver/` 的唯一权威版本记录，同时被 `tools/env_check.py` 的
`driver_source` 检查项解析：脚本会从本文件读取 64 位 SHA-256，并与
`tools/driver/chromedriver.exe` 实际哈希比对，不一致即判定 `BLOCKED`。

## 1. 当前固定版本（本机实测）

| 项目 | 值 |
|---|---|
| ChromeDriver 版本 | `156.0.8078.80` |
| 版本串（`--version` 实际输出） | `ChromeDriver 156.0.8078.80 (fb096c0011f9d50f0a264a9376420cdea9c421e3-refs/branch-heads/8078@{#1705})` |
| 文件名 | `tools/driver/chromedriver.exe` |
| 平台 | Windows x86_64（Chrome for Testing 平台标签 `win64`） |
| 架构 | 64-bit |
| 文件大小 | `24290304` 字节 |
| SHA-256 | `95AE04AEBD7DAF845DCE58D42139F0ACBF1A5172FD480DB328EA70BDC6301790` |
| 下载 URL | `https://storage.googleapis.com/chrome-for-testing-public/156.0.8078.80/win64/chromedriver-win64.zip` |
| 下载时间（UTC） | `2026-10-30T16:42:37Z`（本地 2026-10-31 00:42:37 +08:00） |
| 下载 HTTP 状态 | `200` |
| 压缩包大小 | `11459198` 字节 |
| 压缩包 SHA-256 | `D9E6AC0F49EAD56069E4809384E21E024BAAA924B6C8BFE0E593506499C57364` |
| 官方文件 `Last-Modified` | `Wed, 28 Oct 2026 22:52:52 GMT` |

来源：Chrome for Testing 官方元数据 `last-known-good-versions-with-downloads.json`
的 Stable 通道（该通道在本机下载时给出的版本为 `156.0.8078.80`）。

## 2. 对应浏览器

| 项目 | 值 |
|---|---|
| 本机 Chrome 路径 | `C:\Users\<user>\AppData\Local\Google\Chrome\Application\chrome.exe` |
| 本机 Chrome 版本 | `156.0.8078.76`（2026-10-31 复核；基线记录为 .74，Chrome 自动更新补丁，主版本未变。取自 PE 版本资源，`chrome.exe --version` 在 Windows 已有会话时不可靠） |
| 主版本一致性 | 驱动 156 == 浏览器 156 |

> Chrome 自动更新可能把浏览器升级到 157，此时 `python tools/env_check.py` 会立刻
> 以 `driver_major_match=BLOCKED` + 退出码 2 报错，按第 6 节升级驱动即可。

## 3. 归档（回滚用，未删除）

| 项目 | 值 |
|---|---|
| 归档路径 | `tools/driver/archive/chromedriver-155.0.8059.84.exe` |
| 归档版本 | `155.0.8059.84` |
| 归档文件大小 | `24634368` 字节 |
| 归档 SHA-256 | `2D9A190089EC8546E955479B4BA6866EAEA5D63E1AFB050B5B97662F4DBAD41B` |
| 归档原因 | 与 Chrome 156 主版本不一致（审计 P0-2），已由 156.0.8078.80 替换 |

## 4. 校验记录（真实执行）

```text
> tools\driver\chromedriver.exe --version
ChromeDriver 156.0.8078.80 (fb096c0011f9d50f0a264a9376420cdea9c421e3-refs/branch-heads/8078@{#1705})
> Get-FileHash tools\driver\chromedriver.exe -Algorithm SHA256
95AE04AEBD7DAF845DCE58D42139F0ACBF1A5172FD480DB328EA70BDC6301790
```

解压包内同时附带 `LICENSE.chromedriver`（已复制到 `tools/driver/LICENSE.chromedriver`）。

## 5. 目录结构

```text
tools/driver/
├── chromedriver.exe                     # 当前固定版本 156.0.8078.80
├── LICENSE.chromedriver                 # 随包许可证
├── DRIVER.md                            # 本文件（版本与校验权威记录）
└── archive/
    └── chromedriver-155.0.8059.84.exe   # 旧版本，保留回滚
```

## 6. 升级步骤

1. 查询官方 Stable 版本：
   `https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json`
2. 下载对应 `win64/chromedriver-win64.zip`，确认 HTTP 200。
3. 解压并执行 `chromedriver.exe --version`，确认版本号与浏览器主版本一致。
4. 计算 `Get-FileHash -Algorithm SHA256` 与文件字节数。
5. 把现有 `tools/driver/chromedriver.exe` **复制**到
   `tools/driver/archive/chromedriver-<旧版本>.exe`（不删除、不覆盖历史归档）。
6. 用新文件覆盖 `tools/driver/chromedriver.exe`，同步更新 `LICENSE.chromedriver`。
7. 更新本文件第 1、3、4 节：版本、大小、SHA-256、下载 URL、下载时间、归档记录。
8. 运行 `python tools/env_check.py`，必须 `verdict=READY` 且退出码 `0`（`--strict` 下也是 `0`）。
9. 运行一次 TodoMVC 回归确认会话可建立：
   `python tools/run_selenium.py --run-id <RUN> --target https://demo.playwright.dev/todomvc --capture-pass`

## 7. 回滚步骤

```powershell
Copy-Item tools\driver\archive\chromedriver-155.0.8059.84.exe tools\driver\chromedriver.exe -Force
```

回滚后必须同步改回本文件第 1 节的版本与 SHA-256，否则 `driver_source` 会 `BLOCKED`
（这是预期行为：版本记录必须与磁盘文件一致）。

## 8. 定位约定

`tests/conftest.py` 与 `tools/run_selenium.py` 通过项目内固定路径使用该驱动，
不依赖系统 PATH，也不依赖 Selenium Manager 自动下载。若驱动被移动到别处，
`chromedriver_binary` 检查会直接 `BLOCKED`。
