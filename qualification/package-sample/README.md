# package-sample  （G4 fixture）

- `good/submission/<RUN>/`：结构齐全、xlsx 可打开、zip 可解压、manifest.json 中每个文件
  sha256 与磁盘一致 → **G4 PASS**
- `broken/submission/<RUN>/`：打包后 `screenshots/TC-SAMPLE-002.png` 被替换，哈希不再匹配
  → **G4 FAIL**（`PACKAGE_HASH_MISMATCH`）

这两个目录只用于验证 `--submission` 分支，不属于任何真实交付包，
`official_format_confirmed=false` 标明格式未经官方确认。
