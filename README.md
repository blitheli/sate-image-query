# sate-image-query

按地点或区域, 时间范围, 光学或 SAR 等条件查询卫星影像并下载的 Python 库与 CLI. 数据源清单见 [config/sources.yaml](config/sources.yaml).

## 安装

```bash
python3 -m pip install -e ".[dev]"
```

复制 [.env.example](.env.example) 为 `.env` 并填写需凭据的平台 (不要将 `.env` 提交到仓库).

## 命令行

```bash
python3 -m sate_image_query sources-list
python3 -m sate_image_query sources-test --id mpc-stac --smoke-search
python3 -m sate_image_query search --source mpc-stac \
  --start 2020-06-01T00:00:00Z --end 2020-06-15T00:00:00Z \
  --bbox -122.5 37.7 -122.3 37.9 --modality optical --limit 5
```

## 测试

默认 `pytest` 仅跑离线单元测试. 含网络的集成测试:

```bash
python3 -m pytest -m integration -q
```

带凭据的 CDSE/USGS 测试需在环境中设置相应变量后运行 `requires_credentials` 用例.

## Cursor Skill

代理使用说明见 [.cursor/skills/satellite-imagery-query/SKILL.md](.cursor/skills/satellite-imagery-query/SKILL.md).