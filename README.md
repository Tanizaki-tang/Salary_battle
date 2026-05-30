# Salary Battle（劳资拉扯模拟器）

一个面向求职场景的谈薪模拟项目。当前阶段以**在线版**为主，后端采用 `HR Agent + 语音工具` 主链路，并提供前端 `mock` 运行时兜底。

## 当前状态

- 本期主交付：在线 `HTML` 版本（`Vue + FastAPI + SQLite + sherpa-onnx`）
- 团队分工：`1 人核心链路 + 2 人核心功能`
- 已有后端骨架：健康检查、开局、Agent回合决策、语音回合、结算与落库
- 已有前端骨架：开始页、对话页、结果页 + `api/mock` 双适配器

## 目录结构

```text
Salary_battle/
├─ backend/
│  ├─ app/
│  │  ├─ api/                    # FastAPI 路由（REST + WebSocket）
│  │  ├─ modules/
│  │  │  ├─ agent/               # HR Agent 决策主模块
│  │  │  ├─ flow_controller/     # 编排、状态机、阶段策略、结算、落库
│  │  │  └─ voice_battle/        # 语音识别能力模块
│  │  ├─ prompt/                 # 角色/陷阱 prompt
│  │  ├─ repositories/           # 场景数据
│  │  ├─ service/                # LLM 环境配置
│  │  ├─ shared_types/           # 统一输入输出类型
│  │  └─ main.py                 # FastAPI 入口
│  ├─ scripts/                   # 本地 demo
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
  - `backend/app/modules/flow_controller/`
- **成员 B（Agent能力）**
  - `backend/app/modules/agent/`
- **成员 C（语音功能）**
  - `backend/app/modules/voice_battle/`

原则：模块间通过 `shared_types` 约定数据结构，编排逻辑集中在 `flow_controller/orchestrator.py`。

### GM 场景 Prompt（scene_001）

`scene_001`（初创公司后端岗）使用 Game Master Markdown 作为 HR Agent 的 system prompt 主体，文件位于：

- `backend/scenarios/scene_001_gm.md`

加载逻辑：`backend/app/prompt/scenario_loader.py` → `character_prompt.get_scene_prompt()`。

包含章节：HR 人设、场景设定、意图分类、陷阱机制、数值管理、回复指南、Few-Shot 示例对话。`scene_001` 会跳过 `traps_prompt.py` 以避免重复占 token；`scene_002/003` 仍用短场景描述 + traps。

可选环境变量：

```env
SCENARIO_GM_PATH=D:\path\to\custom_gm.md
```

验收测试：

```bash
cd backend
python tests/test_scenario_loader.py
```

## 快速启动

## 1) 启动后端

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 语音 ASR（实时 / 百炼 Paraformer）

WebSocket 实时通话可切换为“真流式”ASR：浏览器以 PCM 帧上行，后端转发到百炼 Paraformer 实时 ASR，并把增量结果下发为 `server.asr_partial`。

#### 1) 后端环境变量

- `REALTIME_ASR_PROVIDER=bailian`
- `DASHSCOPE_API_KEY=你的百炼 API Key`
- `BAILIAN_ASR_MODEL=paraformer-realtime-v2`（浏览器麦克风推荐；`paraformer-realtime-8k-v2` 仅支持 8000Hz）
- `BAILIAN_ASR_SAMPLE_RATE=16000`

#### 2) 前端环境变量

- `VITE_REALTIME_ASR_PCM=true`
- `VITE_REALTIME_ASR_SAMPLE_RATE=16000`

#### 3) 诊断接口

```bash
curl http://127.0.0.1:8000/api/v1/voice/verify
```

### 语音 TTS 配置（sherpa-onnx / VITS）

实时语音 WebSocket 可启用**后端 TTS**（服务端合成 wav，前端直接播放）。推荐模型 `sherpa-onnx-vits-zh-ll`（中文 5 说话人，可与 HR 人格绑定）。

#### 1) 下载 TTS 模型

```powershell
cd D:\School\HackSong\Salary_battle\models
curl.exe -L -o vits-zh-ll.tar.bz2 https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/sherpa-onnx-vits-zh-ll.tar.bz2
tar -xjf vits-zh-ll.tar.bz2
```

#### 2) 环境变量

- `REALTIME_TTS_ENABLED=true`
- `REALTIME_TTS_MODE=backend`
- `SHERPA_ONNX_TTS_MODEL_TYPE=vits`
- `SHERPA_ONNX_TTS_MODEL_DIR=D:\School\HackSong\Salary_battle\models\sherpa-onnx-vits-zh-ll`
- 可选：`SHERPA_ONNX_TTS_SPEED=1.0`

HR 人格 → 说话人 ID（`backend/app/modules/voice_battle/tts_voice_map.py`）：

| 人格 | sid |
|------|-----|
| hr_newbie | 0 |
| hr_robot | 1 |
| hr_aggressive | 2 |
| hr_honest | 3 |
| hr_smiling_tiger | 4 |

> CosyVoice 不属于 sherpa-onnx 栈；若需 CosyVoice 将在后续迭代单独集成。

#### 3) TTS 验收

```bash
curl -X POST http://127.0.0.1:8000/api/v1/speech/tts -H "Content-Type: application/json" -d "{\"text\":\"你好，我是HR。\"}"
```

`GET /api/v1/voice/verify` 在 `REALTIME_TTS_MODE=backend` 时会额外检查 TTS 模型加载与样例合成。

### 实时通话模式（VoicePage）

进入语音页后自动常开麦 + VAD 检测，停顿约 1 秒自动提交，无需按住说话。

前端 VAD 可调（`.env`）：

- `VITE_VAD_SILENCE_MS=900` — 静音多久视为说完
- `VITE_VAD_MIN_SPEECH_MS=500` — 最短有效语段（过滤杂音短触发）
- `VITE_VAD_ATTACK_MS=280` — 持续超过阈值多久才算开始说话
- `VITE_VAD_CALIBRATION_MS=900` — 进页后自动校准环境底噪
- `VITE_VAD_COMMIT_COOLDOWN_MS=1200` — 每次提交后冷却，避免连环识别

WebSocket 扩展事件：

- `client.barge_in` / `server.barge_in_ack` — 用户打断 HR 播报
- `server.call_state` — `listening` / `thinking` / `speaking`
- `server.asr_skipped` — 未识别到语音时静默恢复（不断线）

也提供 HTTP 接口：`POST /api/v1/speech/tts`，请求体 `{"text":"..."}`，返回 `audio_b64`（wav）。

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
