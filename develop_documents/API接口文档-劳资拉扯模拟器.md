# 劳资拉扯模拟器 API 接口文档（24H 黑客松版）

## 1. 文档说明

- 面向对象：前端开发、后端开发、测试同学。
- 版本：`v1.2`
- 协议：`HTTP/HTTPS + JSON`
- 编码：`UTF-8`
- 目标：支撑双交付通道（在线 HTML + Electron 离线包）的统一 API 闭环（开始对局 -> 多轮谈判 -> 结算落库 + 语音转文本）。

> 说明：项目支持 `mock` 本地模式。在 `mock` 模式下前端不调用任何 API，本文件仅适用于 `api` 模式（在线/离线两通道通用）。

---

## 2. 基础信息

## 2.1 Base URL

- 在线 HTML 版本：`https://your-domain.com`
- 离线包运行（Electron 内置 FastAPI）：`http://127.0.0.1:18080`
- 开发调试（可选）：`http://127.0.0.1:8000`

建议在前端使用统一配置：

```text
VITE_API_BASE_URL=<对应通道的 Base URL>
```

## 2.2 统一请求头

```http
Content-Type: application/json
```

语音上传接口使用 `multipart/form-data`。

## 2.3 鉴权说明

24H 版本不做完整鉴权。使用游客 `user_id` 作为用户标识：

- 前端首次进入生成 `user_id`（建议 UUID）。
- 每次开局时携带 `user_id`。
- 后端按 `user_id` 归档对局成绩。

---

## 3. 统一响应结构

所有接口统一返回：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

- `code = 0` 表示成功
- `code != 0` 表示失败

---

## 4. 数据结构定义

## 4.1 SessionState

```json
{
  "session_id": "sess_001",
  "user_id": "user_abc123",
  "status": "ongoing",
  "round_index": 1,
  "max_round": 5,
  "hr_patience": 80,
  "info_exposure": 30,
  "trap_count": 1
}
```

## 4.2 TurnResult

```json
{
  "hr_reply": "这个薪资已经是应届生统一标准了。",
  "delta": {
    "hr_patience": -5,
    "info_exposure": -3,
    "trap_count": 1
  },
  "is_trap_hit": true,
  "is_game_over": false,
  "next_round": 2
}
```

## 4.3 SettleResult

```json
{
  "final_salary": 12800,
  "final_score": 82,
  "grade": "A",
  "review_tip": "你成功压低了信息暴露度，但可进一步提升陷阱识别稳定性。"
}
```

---

## 5. 接口清单（双通道）

- `GET /api/v1/health` 服务健康检查
- `POST /api/v1/sessions` 开始新对局
- `POST /api/v1/sessions/{session_id}/text-turn` 纯文字对话接口
- `POST /api/v1/sessions/{session_id}/voice-turn` 语音对话接口（接入 sherpa-onnx）
- `POST /api/v1/sessions/{session_id}/settle` 结算并落库
- `POST /api/v1/speech/asr` 原子语音识别接口（可选，调试/预识别）

---

## 6. 详细接口定义

## 6.1 健康检查接口（Health）

- **Method**：`GET`
- **Path**：`/api/v1/health`
- **描述**：用于服务存活探测与部署后巡检，不依赖业务参数。

前端-->后端：
```json
{}
```

后端-->前端：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "healthy",
    "service": "salary-battle-api",
    "version": "v1.2"
  }
}
```

### 说明

- 建议部署平台将此接口作为健康探针（Health Check URL）。
- 若后端进程异常或路由不可达，应返回非 2xx，由平台自动重启。

---

## 6.2 开始新对局

- **Method**：`POST`
- **Path**：`/api/v1/sessions`
- **描述**：创建新对局并返回初始状态、首句 HR 话术、场景元数据。

前端-->后端：
```json
{
  "user_id": "user_abc123",
  "scene_id": "scene_001",
  "role_id": "role_backend"
}
```

后端-->前端：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "session": {
      "session_id": "sess_001",
      "user_id": "user_abc123",
      "scene_id": "scene_001",
      "role_id": "role_backend",
      "status": "ongoing",
      "round_index": 1,
      "max_round": 5,
      "hr_patience": 80,
      "info_exposure": 20,
      "trap_count": 0
    },
    "hr_opening": "你好！我们给你的初始 offer 是 15K*14，你怎么看？",
    "scene_meta": {
      "scene_id": "scene_001",
      "scene_name": "初创公司后端岗",
      "role_hint": "后端开发求职者"
    }
  }
}
```

### 字段说明

- `hr_opening`：首轮 HR 开场话术。
- `status`：`ongoing | settled | closed`。

---

## 6.3 纯文字对话接口（Text Turn）

- **Method**：`POST`
- **Path**：`/api/v1/sessions/{session_id}/text-turn`
- **描述**：仅接受文本输入（策略值或自由文本），推进一回合并返回状态变化。

### Path 参数

- `session_id`：对局 ID

前端-->后端（策略模式）：
```json
{
  "strategy": "probe"
}
```

前端-->后端（自由文本模式）：
```json
{
  "player_text": "我想先确认一下这个岗位的薪资区间和加班费计算方式。"
}
```

后端-->前端：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "result": {
      "hr_reply": "你问得很专业，你先说说你关心的重点。",
      "delta": {
        "hr_patience": -2,
        "info_exposure": 5,
        "trap_count": 0
      },
      "is_trap_hit": false,
      "is_game_over": false,
      "next_round": 2
    },
    "session": {
      "session_id": "sess_001",
      "user_id": "user_abc123",
      "scene_id": "scene_001",
      "role_id": "role_backend",
      "status": "ongoing",
      "round_index": 2,
      "max_round": 5,
      "hr_patience": 78,
      "info_exposure": 25,
      "trap_count": 0
    }
  }
}
```

---

## 6.4 语音对话接口（Voice Turn）

- **Method**：`POST`
- **Path**：`/api/v1/sessions/{session_id}/voice-turn`
- **描述**：直接上传语音完成“一次回合推进”。后端内部调用 `sherpa-onnx` 识别，再进入谈判引擎。

### Path 参数

- `session_id`：对局 ID

前端-->后端（multipart/form-data）：
```json
{
  "audio_file": "<binary:wav/mp3/m4a/webm>",
  "input_mode": "voice"
}
```

后端-->前端：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "asr": {
      "transcript": "我想确认一下这个岗位的薪资区间和加班费。",
      "confidence": 0.9
    },
    "result": {
      "hr_reply": "你问得很专业，你先说说你关心的重点。",
      "delta": {
        "hr_patience": -2,
        "info_exposure": 5,
        "trap_count": 0
      },
      "is_trap_hit": false,
      "is_game_over": false,
      "next_round": 2
    },
    "session": {
      "session_id": "sess_001",
      "user_id": "user_abc123",
      "scene_id": "scene_001",
      "role_id": "role_backend",
      "status": "ongoing",
      "round_index": 2,
      "max_round": 5,
      "hr_patience": 78,
      "info_exposure": 25,
      "trap_count": 0
    }
  }
}
```

后端-->前端（失败示例）：
```json
{
  "code": 5002,
  "message": "ASR failed, please retry or use text-turn",
  "data": {
    "hint": "请重试语音，或切换到 text-turn 接口"
  }
}
```

### 业务约束

- `voice-turn` 与 `text-turn` 的回合推进逻辑必须完全一致。
- `voice-turn` 返回结果中必须包含 `asr.transcript`，便于前端展示“识别文本”。
- 若 ASR 失败，不推进回合（`round_index` 不变）。

---

## 6.5 对局结算并落库

- **Method**：`POST`
- **Path**：`/api/v1/sessions/{session_id}/settle`
- **描述**：计算最终评分并将 `user_id + final_score` 持久化到数据库。

### Path 参数

- `session_id`：对局 ID

前端-->后端：
```json
{}
```

后端-->前端：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "result": {
      "final_salary": 17800,
      "final_score": 58,
      "grade": "C",
      "review_tip": "你成功控制了信息暴露度，建议继续提升陷阱识别稳定性。"
    },
    "persist": {
      "saved": true,
      "user_id": "user_abc123",
      "session_id": "sess_001"
    }
  }
}
```

### 业务约束

- 结算成功后，`session.status` 必须更新为 `settled`。
- 必须保证数据库中可按 `user_id` 查询到本局 `final_score`。

---

## 6.6 语音转文本原子接口（sherpa-onnx）

- **Method**：`POST`
- **Path**：`/api/v1/speech/asr`
- **描述**：仅执行语音识别，不推进回合。用于调试、预识别、弱网兜底。

前端-->后端（multipart/form-data）：
```json
{
  "audio_file": "<binary:wav/mp3/m4a/webm>"
}
```

后端-->前端：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "transcript": "我想确认一下试用期薪资和转正后的基数。",
    "confidence": 0.9
  }
}
```

### 失败兜底建议

- 当前端收到低置信度结果（例如 `< 0.6`）时，提示用户改为文本输入。

---

## 7. 错误码定义

| 错误码 | 含义 | 处理建议 |
|---|---|---|
| `0` | 成功 | 正常处理 |
| `4001` | 参数错误 | 检查必填字段与字段类型 |
| `4004` | session 不存在 | 提示重新开局 |
| `4009` | session 已结束 | 引导进入结果页 |
| `4010` | user_id 缺失或非法 | 重新生成游客 ID |
| `5000` | 服务内部异常 | 展示重试按钮并记录日志 |
| `5002` | ASR 识别失败 | 回退文本输入 |

> 黑客松阶段建议前端统一对 `code != 0` 显示 Toast，并带“重试”按钮。

---

## 8. 最小联调流程（前后端）

1. 前端调用 `POST /api/v1/sessions` 创建对局。
2. 回合中二选一：
   - 纯文字：调用 `POST /api/v1/sessions/{id}/text-turn`。
   - 语音：调用 `POST /api/v1/sessions/{id}/voice-turn`（推荐一体化链路）。
3. 可选调试链路（非主链路）：
   - 先调 `POST /api/v1/speech/asr` 拿 `transcript`，再调用 `text-turn`。
4. 游戏结束后调用 `POST /api/v1/sessions/{id}/settle`。
5. 检查返回 `persist.saved = true`，确认 `final_score` 已落库。

---

## 9. 示例 cURL

```bash
# 按运行通道切换：
# 在线 HTML: BASE_URL="https://your-domain.com"
# Electron 离线包: BASE_URL="http://127.0.0.1:18080"
# 本地调试: BASE_URL="http://127.0.0.1:8000"
```

## 9.1 健康检查

```bash
curl -X GET "$BASE_URL/api/v1/health"
```

## 9.2 创建对局

```bash
curl -X POST "$BASE_URL/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"user_abc123\"}"
```

## 9.3 纯文字回合

```bash
curl -X POST "$BASE_URL/api/v1/sessions/sess_001/text-turn" \
  -H "Content-Type: application/json" \
  -d "{\"strategy\":\"probe\"}"
```

## 9.4 语音回合

```bash
curl -X POST "$BASE_URL/api/v1/sessions/sess_001/voice-turn" \
  -F "audio_file=@./demo.wav"
```

## 9.5 结算

```bash
curl -X POST "$BASE_URL/api/v1/sessions/sess_001/settle" \
  -H "Content-Type: application/json" \
  -d "{}"
```

## 9.6 原子语音识别

```bash
curl -X POST "$BASE_URL/api/v1/speech/asr" \
  -F "audio_file=@./demo.wav"
```

---

## 10. 变更记录

- `v1`：黑客松最小可用 API，覆盖对局主链路、结算落库、sherpa-onnx 语音转文本。
- `v1.1`：将回合接口拆分为 `text-turn` 与 `voice-turn` 双通道，语音接口支持一体化“识别+推进回合”。
- `v1.2`：对齐双交付通道（在线 HTML + Electron 离线包），更新 Base URL 与联调/cURL 规范。
