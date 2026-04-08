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

## 数据源说明

> 提醒: 涉及账号注册的数据源, 请先在对应官网注册, 再在 `.env` 中填写用户名和密码等参数.

| 数据源ID | 平台/简介 | 主要卫星型号(示例) | 典型空间分辨率 | 典型更新频率 | 认证与配置 |
| --- | --- | --- | --- | --- | --- |
| `mpc-stac` | Microsoft Planetary Computer STAC, 统一 STAC 检索入口, 适合快速跨任务检索. | Sentinel-2, Landsat 8/9, Sentinel-1 | Sentinel-2: 10m(部分波段), Landsat: 30m, Sentinel-1 GRD: 10m | 近实时到日级更新, 取决于具体集合与处理链 | 通常匿名可查, 无必填凭据 |
| `cdse-odata` | Copernicus Data Space Ecosystem OData, 欧空局哥白尼官方生态接口. | Sentinel-1, Sentinel-2, Sentinel-3, Sentinel-5P(按产品可选) | Sentinel-2: 10m/20m/60m, Sentinel-1 GRD: 10m | 日级持续更新(按轨道与产品处理进度) | 需要账号, 在 `.env` 配置 `COPERNICUS_USERNAME`, `COPERNICUS_PASSWORD` |
| `usgs-m2m` | USGS EarthExplorer M2M API, 面向 Landsat 等数据的程序化检索接口. | Landsat 4-9(常用 Collection 2 Level-2) | 30m(多光谱), 15m(全色, 部分任务) | 约 16 天重访(单星), 多星组合可缩短 | 需要账号, 在 `.env` 配置 `USGS_M2M_USERNAME`, `USGS_M2M_PASSWORD` |
| `crsda-web` | 中国资源卫星数据服务网, 当前以网页检索/订购流程为主. | 资源系列, 高分系列等(以平台发布为准) | 米级到十米级(按卫星与产品类型变化) | 按任务与数据发布节奏更新 | 主要为网页流程, 建议先注册账号, 当前仓库未提供稳定公开API自动化 |
| `gscloud-web` | 地理空间数据云, 国内常用遥感与DEM数据门户. | Landsat, Sentinel, 国产数据与DEM(以门户目录为准) | 约 10m-30m(光学常见), DEM 常见 30m | 依数据集而定, 周期性更新 | 主要为网页流程, 建议先注册账号, 当前仓库按 `web_manual` 管理 |

> 说明: 表中“分辨率”“更新频率”为常见范围, 实际以具体产品, 区域覆盖和平台发布信息为准.

## Cursor Skill

代理使用说明见 [.cursor/skills/satellite-imagery-query/SKILL.md](.cursor/skills/satellite-imagery-query/SKILL.md).