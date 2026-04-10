# AGENTS.md

## Cursor Cloud specific instructions

### 概述

本仓库是查询并创建SKILL或者相关python代码库,用户从网络获取指定地点和指定时间范围的卫星影像,并附带其它查询条件

### 注意事项

- 所有交互尽量按照中文, 使用英文符号: ,:"等
- 查询和下载卫星影像的网站需要注册，用户名等信息时，请提醒我，并预留在.env文件中预留相应参数设置
- 必要时安装相应的skill
- 假设我并不清楚所有的开发过程，你更新方案时需要和我迭代确认

### 开发环境

- **Python >= 3.10**, 当前 VM 已有 Python 3.12.
- 安装依赖: `python3 -m pip install -e ".[dev]"` (详见 README).
- `.env` 文件从 `.env.example` 复制而来, 填写凭据后可解锁 CDSE/USGS 数据源; MPC STAC 无需凭据.
- 本项目是纯 CLI/库, 无本地服务需要启动.

### 测试与 Lint

- 离线单元测试: `python3 -m pytest` (默认排除 `integration` 和 `requires_credentials` 标记).
- 集成测试(需网络): `python3 -m pytest -m integration -v`.
- 带凭据测试: `python3 -m pytest -m requires_credentials -v` (需 `.env` 中配置 `COPERNICUS_*` 或 `USGS_M2M_*`).
- 本项目暂无独立 lint 工具配置(无 flake8/ruff/mypy 等).

### CLI 验证

- `python3 -m sate_image_query sources-list` — 列出所有已配置数据源.
- `python3 -m sate_image_query sources-test --id mpc-stac --smoke-search` — 健康检查 + 小范围搜索.
- `python3 -m sate_image_query search --source mpc-stac --start ... --end ... --bbox ... --modality optical --limit N` — 实际搜索.

### 注意

- `planetary_computer` 库会产生 Pydantic V2 deprecation warning, 不影响功能.
- CDSE 和 USGS 集成测试在无凭据时自动跳过, 不会失败.