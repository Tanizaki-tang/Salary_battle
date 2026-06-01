# Salary Battle（劳资拉扯模拟器）

一个面向求职场景的谈薪模拟项目。当前为**纯文字**在线版：前端 `Vue` + 后端 `FastAPI + HR Agent`，支持 `api/mock` 双运行时。

## 当前状态

- 主链路：`StartPage → BattlePage → ResultPage`
- API：`POST /sessions`、`/text-turn`、`/settle`
- 已有后端：健康检查、开局、文字回合、结算与落库（支持 `PostgreSQL`，未配置时本地回退到 `SQLite`）
- 已有前端：开始页、对话页、结果页 + `api/mock` 双适配器

## 目录结构

```text
Salary_battle/
├─ backend/
│  ├─ app/
│  │  ├─ api/                    # FastAPI REST 路由
│  │  ├─ modules/
│  │  │  ├─ agent/               # HR Agent 决策
│  │  │  └─ flow_controller/     # 编排、状态机、结算、落库
│  │  ├─ prompt/                 # 角色/场景 prompt
│  │  ├─ repositories/           # 场景数据
│  │  ├─ service/                # LLM 与历史 payload
│  │  ├─ shared_types/           # 统一类型
│  │  └─ main.py
│  ├─ scripts/
│  ├─ requirements.txt
│  └─ app.db                  # 未配置 DATABASE_URL 时的本地回退库
├─ frontend/
│  ├─ src/pages/
│  ├─ src/runtime/               # api/mock 适配器
│  └─ package.json
└─ README.md
```

### GM 场景 Prompt（scene_001）

`scene_001` 使用 Game Master Markdown 作为 HR Agent system prompt，位于 `backend/scenarios/scene_001_gm.md`。

加载：`backend/app/prompt/scenario_loader.py` → `character_prompt.get_scene_prompt()`。

可选环境变量：

```env
SCENARIO_GM_PATH=D:\path\to\custom_gm.md
```

## 快速启动

### 1) 启动后端

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

推荐先在根目录 `.env` 配置正式数据库：

```env
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/salary_battle
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/v1/health
```

### 2) 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认连接 `VITE_API_BASE_URL`（未配置时为 `http://127.0.0.1:8000`）。

### 前端变体（开发版 / 正式版）

| 变体 | 命令 | 开始页能力 |
|------|------|------------|
| **开发版** `dev` | `npm run dev` | 昵称、角色、场景、HR 性格选择 |
| **正式版** `prod` | `npm run build` | 仅昵称 + 职位；HR 性格服务端随机 |

```env
VITE_APP_VARIANT=dev   # 本地开发
VITE_APP_VARIANT=prod  # 生产构建
```

本地打包开发版 UI：`npm run build:dev-ui`。

### 3) 本地验收脚本

```bash
cd backend
python scripts/run_local_demo.py
```

### 4) Docker

```bash
docker build -t salary-battle-api:latest .
docker run --rm -p 8000:8000 --name salary-battle-api salary-battle-api:latest
```

## API 概览

见根目录 `API接口文档-劳资拉扯模拟器.md`。

## 文档索引

- 技术方案：`develop_documents/技术方案-劳资拉扯模拟器.md`
- 在线版架构：`develop_documents/项目架构与核心链路-在线版.md`
- 部署指南：`develop_documents/部署指南-Render-Netlify.md`
