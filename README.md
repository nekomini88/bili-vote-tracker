# Bili Vote Tracker 🗳️

奥特曼人气投票实时监控面板 —— 抓取 Bilibili 活动投票数据，实时展示全部 46 位奥特曼候选人的票数、各时段增量与趋势图表，自带主题切换与地域/浏览器信息条。

## ✨ 功能特性

- **实时轮询采集**：后台定时从 Bilibili 投票活动**分页抓取全部候选人**票数并落库（SQLite）
- **候选人主表**：全部 46 位奥特曼按**得票数从大到小**排序，显示当前票数 + 1m/5m/30m/6h/24h 环比增量，每行附**官方立绘头像**
- **多维图表**：
  - 📈 趋势线（票数随时间走势）
  - 📊 票数对比（当前各候选人票数）
  - 📉 增量柱状（每轮采集的票数增量）
  - 支持「按时间段查询」自定义起止区间
- 🎨 **奥特曼主题**：红蓝能量光效背景 + 46 位官方立绘头像 + 双主题光点 logo
- 📱 **响应式**：手机端 stats 自动折叠 (2/1 列)、控件自适应、表格触摸滚动
- 🌍 地域 Footer：国旗 + 国家 · 城市 · IP · 浏览器，点击展开，随 30s 自动刷新
- 🔐 管理员后台：登录后可修改目标地址与采集间隔（HTTP Basic Auth）

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose
- 一个 Bilibili 投票活动（`b23.tv` 短链或页面 URL）

### 运行

```bash
docker compose up -d --build
```

访问 `http://<host>:9008`。

## ⚙️ 配置

服务通过环境变量配置（`docker-compose.yml`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `9008` | 服务端口 |
| `TARGET_URL` | `https://b23.tv/wDz5Xnc` | 目标活动页短链 |
| `DB_PATH` | `/app/db/votes.db` | SQLite 数据库路径 |
| `POLL_INTERVAL` | `1` | 轮询间隔（分钟） |
| `ADMIN_USER` | `admin` | 管理后台账号 |
| `ADMIN_PASS` | `nekomini` | 管理后台密码 |

> 后台配置也可运行时在线修改，保存后立即生效。

## 🔌 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/latest` | GET | 所有候选人的最新票数（每候选人一条） |
| `/api/history?title=<候选人>` | GET | 单个候选人的票数历史 |
| `/api/range?title&start&end` | GET | 指定时间范围的历史 |
| `/api/diff?title=` | GET | 1m/5m/30m/6h/24h 环比增量 |
| `/api/stats` | GET | 总采集数、最高票、均值、候选人数等 |
| `/api/config` | GET/POST | 读取 / 更新配置（需 Basic Auth） |
| `/api/trigger` | GET | 手动触发一次采集（需 Basic Auth） |
| `/api/my-info` | GET | 请求者 IP 地域信息（按 IP 缓存） |
| `/healthz` | GET | 健康检查 |

## 🗂️ 项目结构

```
bili-vote-tracker/
├── backend/
│   └── app.py            # FastAPI 后端：分页采集调度 + 数据 API
├── frontend/
│   ├── index.html        # 单页前端（内联 CSS/JS）
│   ├── assets/heroes/    # 46 位奥特曼官方立绘头像
│   ├── assets/vendor/    # 本地自托管 Tailwind browser build
│   └── generate_heroes.py# 头像生成脚本（占位版）
├── db/
│   └── votes.db          # SQLite（gitignore，不入库）
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── VERSION               # 版本号（镜像内暴露）
```

## 🛠️ 技术栈

- **后端**：FastAPI + Uvicorn + APScheduler + SQLite
- **前端**：原生 HTML/CSS/JS + Canvas 图表 + 本地 Tailwind (browser build)
- **部署**：Docker Compose

## 📈 数据说明

- 候选人为**全部 46 位**奥特曼，后端用 `pn` 分页拉取（接口 `page.total` 决定页数，`page_num` 参数无效需用 `pn`）
- 前端 `rankSort` 按 `votes` 从大到小排序，票数相同按中文名 `localeCompare` 稳定排序
- 新入库候选（无历史对比点）diff 显示为灰色 `0`，老候选显示真实增量
- `captured_at` 使用 UTC+8 本地时间，秒级精度
- 同秒重复写入通过 `INSERT OR IGNORE` + `idx_vote_records_unique` 唯一索引(item_id) 去重

## 🔬 测试

### 单元测试（前端纯逻辑，Node 22+ 内置，零依赖）
```bash
node --test frontend/logic.test.js
```
覆盖：`HERO_IDS` 46 位映射、`heroSrc` 头像路径、`rankSort` 票数降序/中文稳定、`fmt` 千分位、`fmtDelta` 零值/正负、`countryCodeToFlag` 国旗。

### API 集成测试（对运行中的容器端到端）
```bash
python3 tests/api_test.py
```
覆盖：`/healthz` 版本、`/api/stats` 版本、`/api/latest` 返回全部 46 位候选人、记录结构、`/api/diff` 真实增量、`/api/history`。

> 测试发现并修复了 `countryCodeToFlag` 只生成单字符国旗的 bug。

## 🔧 开发与调试

本地构建验证：

```bash
python3 -m py_compile backend/app.py   # 后端语法检查
docker compose up -d --build           # 重建部署
curl http://127.0.0.1:9008/healthz     # 健康检查
```

> 完整的调试与架构教训见 Hermes 技能 `bili-vote-tracker-debug`（scheduler 单例、/api/latest 子查询、Geo 按 IP 缓存、前端 diff 并行化、pn 分页拉全、主题对齐）。

## 🚀 发版流程

版本号记录在 `VERSION` 文件（当前 `1.1.2`）。发版 = **git tag + gh release**：

```bash
# 1. 更新 VERSION 与代码并提交
git add -A && git commit -m "v1.1.2: <变更说明>"

# 2. 打 tag 并推送
git tag v1.1.2
git push origin main --tags

# 3. 创建 GitHub Release
gh release create v1.1.2 --title "v1.1.2" --notes "<变更说明>"
```

> 镜像由部署端 `docker compose up -d --build` 构建，无需推送镜像仓库；`VERSION` 文件会在容器内 `/healthz` 中暴露。

## 📄 License

[MIT](LICENSE)