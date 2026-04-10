---
name: satellite-imagery-query
description: 按地点/区域, 时间, 分辨率意图与光学或 SAR 类型查询并下载卫星影像时使用本仓库的 Python CLI 与配置约定.
---

# 卫星影像查询与下载 (sate-image-query)

## 何时使用

- 用户需要从网络按经纬度或边界框, 时间范围, 影像类型 (光学, SAR) 等条件检索可用景并下载.
- 需要列出或验证「有效数据源」连通性与凭据.

## 前置条件

1. 在项目根目录安装: `python3 -m pip install -e ".[dev]"`.
2. 需要凭据的数据源在根目录复制 `.env.example` 为 `.env` 并填写, **切勿将 `.env` 提交到 Git**.
3. 各平台账号需用户自行在对应网站注册, 本 Skill 不提供账号.

## CLI 命令 (入口: `python3 -m sate_image_query` 或 `sate-image-query`)

| 命令 | 说明 |
| --- | --- |
| `sources-list` | 列出 `config/sources.yaml` 中的数据源 id |
| `sources-test --id <id> [--smoke-search]` | 健康检查, `--smoke-search` 会做极小范围查询 (可能更慢) |
| `search --source mpc-stac --start ... --end ... --bbox min_lon min_lat max_lon max_lat [--modality optical\|sar\|any] [--limit N] [--json-out path]` | STAC 检索, 输出 JSON (含 `assets` 下载链接) |
| `search --source aws-earth-search ...` | 同上, 使用 [Earth Search](https://earth-search.aws.element84.com/v1) (AWS 上公开数据集的 STAC, 无需凭据) |
| `download --source mpc-stac --scene-json file.json --dest dir [--assets key1,key2]` | 按 `search` 保存的条目下载资产 |

### 示例 (Planetary Computer STAC, 通常无需凭据)

```bash
python3 -m sate_image_query search --source mpc-stac \
  --start 2020-06-01T00:00:00Z --end 2020-06-15T00:00:00Z \
  --bbox -122.5 37.7 -122.3 37.9 --modality optical --limit 5 --json-out scenes.json
```

Copernicus CDSE 与 USGS M2M 需在 `.env` 中配置 `COPERNICUS_*` 或 `USGS_M2M_*` 后使用 `--source cdse-odata` 或 `--source usgs-m2m`.

`aws-earth-search` 与 `mpc-stac` 一样为匿名 STAC; 适合需要与 AWS 上 Landsat / Sentinel-2 等公开桶对齐的检索 (更新通常较快, 具体以各数据集说明为准). 个别资产桶若启用 Requester Pays, 下载时可能需要自行配置 AWS 凭证与计费, 本 CLI 的 `download` 仍按 URL 直连处理.

## 对用户提醒

- 遵守各数据平台服务条款与引用要求.
- 国产网页型门户 (`web_manual`) 仅作目录登记, 自动化检索需人工在网站操作或后续单独开发.

## 相关文件

- 数据源目录: `config/sources.yaml`
- 环境变量模板: `.env.example`
- 包代码: `sate_image_query/`
