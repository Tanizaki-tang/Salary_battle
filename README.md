# Salary Battle（劳资拉扯模拟器）

一个面向求职场景的谈薪模拟项目。当前阶段以**在线版**为主，支持文字回合与语音回合（ASR）两条链路，并提供前端 `mock` 运行时兜底。

## 当前状态

- 本期主交付：在线 `HTML` 版本（`Vue + FastAPI + SQLite + sherpa-onnx`）
- 团队分工：`1 人核心链路 + 2 人核心功能`
- 已有后端骨架：健康检查、开局、文字回合、语音回合、结算与落库
- 已有前端骨架：开始页、对话页、结果页 + `api/mock` 双适配器

## 目录结构

```text
Salary_battle/
├─ backend/
│  ├─ app/
│  │  ├─ api/                    # FastAPI 路由
│  │  ├─ contracts/              # 模块契约（函数签名）
│  │  ├─ modules/
│  │  │  ├─ flow_controller/     # 核心链路：状态、结算、落库
│  │  │  ├─ text_battle/         # 核心功能1：文字回合
│  │  │  └─ voice_battle/        # 核心功能2：语音回合
│  │  ├─ orchestrators/          # 编排层
│  │  ├─ shared_types/           # 统一输入输出类型
│  │  └─ main.py                 # FastAPI 入口
│  ├─ scripts/                   # 契约校验与本地 demo
│  ├─ requirements.txt
│  └─ app.db
├─ frontend/
│  ├─ src/
│  │  ├─ pages/
│  │  ├─ runtime/                # api/mock 双适配器
│  │  ├─ mock/                   # 本地 mock 数据
│  │  └─ api/
│  ├─ package.json
│  └─ index.html
├─ develop_documents/
│  ├─ 技术方案-劳资拉扯模拟器.md
│  ├─ API接口文档-劳资拉扯模拟器.md
│  └─ 项目架构与核心链路-在线版.md
└─ README.md
```

## 分工建议（本期）

- **成员 A（核心链路）**
  - `backend/app/api/`
  - `backend/app/orchestrators/`
  - `backend/app/modules/flow_controller/`
- **成员 B（文字功能）**
  - `backend/app/modules/text_battle/`
- **成员 C（语音功能）**
  - `backend/app/modules/voice_battle/`

原则：模块间通过 `contracts` 与 `shared_types` 交互，避免跨模块直接耦合。

## 快速启动

## 1) 启动后端

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 语音 ASR 配置（sherpa-onnx）

后端语音回合与 `/api/v1/speech/asr` 使用 `sherpa-onnx` 离线识别。启动前配置环境变量：

- `SHERPA_ONNX_MODEL_TYPE=paraformer`（可选值：`paraformer` / `transducer`）
- `SHERPA_ONNX_MODEL_DIR`：模型目录（paraformer 目录内需包含 `tokens.txt` + `model.onnx` 或 `model.int8.onnx`）
- 可选：`SHERPA_ONNX_PROVIDER=cpu`、`SHERPA_ONNX_NUM_THREADS=1`、`SHERPA_ONNX_DECODING_METHOD=greedy_search`

上传音频要求：单声道、16-bit PCM 的 wav 文件。

健康检查：

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## 2) 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认前端会连接 `VITE_API_BASE_URL`，未配置时走 `http://127.0.0.1:8000`。

## 3) 运行后端最小验收脚本

```bash
cd backend
python scripts/combine_modules.py
python scripts/run_local_demo.py
```

## 4) 使用 Docker 启动后端

> 当前 Dockerfile 仅打包后端 FastAPI 服务（在线版核心链路）。

### 构建镜像

```bash
docker build -t salary-battle-api:latest .
```

### 运行容器

```bash
docker run --rm -p 8000:8000 --name salary-battle-api salary-battle-api:latest
```

### 容器内健康检查

```bash
curl http://127.0.0.1:8000/api/v1/health
```

### 持久化 SQLite（可选）

默认数据库位于容器内 `/app/backend/app.db`。如需持久化到宿主机，可挂载卷：

```bash
docker run --rm -p 8000:8000 \
  -v ${PWD}/backend/app.db:/app/backend/app.db \
  --name salary-battle-api salary-battle-api:latest
```

## API 概览
见：`develop_documents/API接口文档-劳资拉扯模拟器.md`


## 文档索引

- 技术方案：`develop_documents/技术方案-劳资拉扯模拟器.md`
- API 文档：`develop_documents/API接口文档-劳资拉扯模拟器.md`
- 在线版架构：`develop_documents/项目架构与核心链路-在线版.md`
- 本地版架构（后续）：`develop_documents/项目架构与核心链路-本地版.md`
