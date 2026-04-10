# usgs-m2m 数据源更新与 Skill 测试记录

## 目标

- 查询 `usgs-m2m` 可用的 `optical` 与 `sar` 数据源.
- 更新 `config/sources.yaml` 的 `usgs-m2m` 配置.
- 按 skill 流程执行测试并记录过程.

## 前置说明

- USGS M2M 需要先在官网注册账号: [https://ers.cr.usgs.gov/register](https://ers.cr.usgs.gov/register)
- 本仓库通过 `.env` 读取凭据, 请先复制 `.env.example` 为 `.env`, 并填写:
  - `USGS_M2M_USERNAME=...`
  - `USGS_M2M_PASSWORD=...`
- 注意: `.env` 不要提交到 Git.

## 执行步骤

### 1) 安装依赖

```bash
python3 -m pip install -e ".[dev]"
```

### 2) 列出现有 source

```bash
python3 -m sate_image_query sources-list
```

期望看到 `usgs-m2m`.

### 3) 查询并更新 usgs-m2m 的 optical/sar 数据集

```bash
python3 -m sate_image_query sources-sync-usgs --id usgs-m2m
```

行为:

- 通过 M2M `dataset-search` 查询可用 dataset.
- 按关键字归类为 `optical` / `sar`.
- 自动更新 `config/sources.yaml` 中:
  - `supports: [optical, sar]`
  - `default_dataset_optical`
  - `default_dataset_sar`

仅预览而不落盘:

```bash
python3 -m sate_image_query sources-sync-usgs --id usgs-m2m --dry-run
```

### 4) 健康检查

```bash
python3 -m sate_image_query sources-test --id usgs-m2m
```

可选冒烟搜索:

```bash
python3 -m sate_image_query sources-test --id usgs-m2m --smoke-search
```

### 5) 按 modality 搜索验证

optical:

```bash
python3 -m sate_image_query search \
  --source usgs-m2m \
  --start 2020-06-01T00:00:00Z --end 2020-06-15T00:00:00Z \
  --bbox -112.5 44.5 -112.0 45.0 \
  --modality optical \
  --limit 2
```

sar:

```bash
python3 -m sate_image_query search \
  --source usgs-m2m \
  --start 2020-06-01T00:00:00Z --end 2020-06-15T00:00:00Z \
  --bbox -112.5 44.5 -112.0 45.0 \
  --modality sar \
  --limit 2
```

验证点:

- `optical` 结果中 `collection` 应使用 `default_dataset_optical` 或显式 `--collections`.
- `sar` 结果中 `collection` 应使用 `default_dataset_sar` 或显式 `--collections`.

## 本次改动摘要

- `usgs-m2m` 配置更新为同时支持 `optical/sar`.
- 新增 `sources-sync-usgs` 命令用于查询并更新 USGS 数据集配置.
- `USGSSource.search()` 现在根据 `--modality` 自动选择默认 dataset.

## 本地实测结果 (Cursor Cloud)

已执行:

- `python3 -m pip install -e ".[dev]"`: 成功.
- `python3 -m pytest tests/test_cli.py tests/test_catalog.py -q`: `5 passed`.
- `python3 -m sate_image_query sources-list`: 成功, 输出包含 `usgs-m2m`.
- `python3 -m sate_image_query sources-sync-usgs --id usgs-m2m --dry-run`: 失败, 原因是当前环境未设置 `USGS_M2M_USERNAME`/`USGS_M2M_PASSWORD`.

结论:

- 代码路径和无凭据失败路径已验证.
- 若要完成在线查询并将 `optical/sar` 可用 dataset 自动回写配置, 需在 `.env` 提供 USGS 账号后重跑步骤 3-5.

