# 劳资拉扯模拟器 API 接口文档（24H 黑客松版）



## 1. 文档说明



- 面向对象：前端开发、后端开发、测试同学。

- 版本：`v1.3`

- 协议：`HTTP/HTTPS + JSON`

- 编码：`UTF-8`

- 目标：支撑文字谈判闭环（开始对局 → 多轮谈判 → 结算落库）。



> 说明：项目支持 `mock` 本地模式。在 `mock` 模式下前端不调用任何 API，本文件仅适用于 `api` 模式。



---



## 2. 基础信息



### 2.1 Base URL



- 在线 HTML 版本：`https://your-domain.com`

- 离线包运行（Electron 内置 FastAPI）：`http://127.0.0.1:18080`

- 开发调试：`http://127.0.0.1:8000`



建议在前端使用统一配置：



```text

VITE_API_BASE_URL=<对应通道的 Base URL>

```



### 2.2 统一请求头



```http

Content-Type: application/json

```



### 2.3 鉴权说明



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



### 4.1 SessionState



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



### 4.2 TurnResult



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



### 4.3 FlowDecision



```json

{

  "next_phase": "text",

  "reason": "default_text_loop",

  "should_end": false

}

```



`next_phase` 取值：`text | end`。



### 4.4 SettleResult



```json

{

  "final_salary": 12800,

  "final_score": 82,

  "grade": "A",

  "review_tip": "你成功压低了信息暴露度，但可进一步提升陷阱识别稳定性。"

}

```



---



## 5. 接口清单



- `GET /api/v1/health` 服务健康检查

- `GET /api/v1/hr-personalities` HR 性格列表（开发版选角）

- `POST /api/v1/sessions` 开始新对局

- `POST /api/v1/sessions/{session_id}/text-turn` 文字对话接口

- `POST /api/v1/sessions/{session_id}/settle` 结算并落库



---



## 6. 详细接口定义



### 6.1 健康检查



- **Method**：`GET`

- **Path**：`/api/v1/health`



后端响应：



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



---



### 6.2 开始新对局



- **Method**：`POST`

- **Path**：`/api/v1/sessions`



请求体：



```json

{

  "user_id": "user_abc123",

  "user_name": "小明",

  "scene_id": "scene_001",

  "role_id": "role_backend",

  "hr_personality_id": "random"

}

```



- `hr_personality_id` 为空或 `random` 时，服务端随机分配 HR 性格（正式版默认行为）。



响应体（节选）：



```json

{

  "code": 0,

  "message": "ok",

  "data": {

    "session": { "session_id": "sess_001", "status": "ongoing", "round_index": 1 },

    "hr_opening": "小明，你好！我们给你的初始 offer 是 15K*14，你怎么看？",

    "scene_meta": { "scene_id": "scene_001", "scene_name": "初创公司后端岗" },

    "hr_personality_meta": { "personality_id": "hr_smiling_tiger", "name": "笑面虎型" }

  }

}

```



---



### 6.3 文字对话（Text Turn）



- **Method**：`POST`

- **Path**：`/api/v1/sessions/{session_id}/text-turn`



策略模式：



```json

{ "strategy": "probe" }

```



自由文本模式：



```json

{

  "player_text": "我想先确认一下这个岗位的薪资区间和加班费计算方式。"

}

```



响应体（节选）：



```json

{

  "code": 0,

  "message": "ok",

  "data": {

    "result": {

      "hr_reply": "你问得很专业，你先说说你关心的重点。",

      "delta": { "hr_patience": -2, "info_exposure": 5, "trap_count": 0 },

      "is_trap_hit": false,

      "is_game_over": false,

      "next_round": 2

    },

    "session": { "round_index": 2, "hr_patience": 78 },

    "flow": { "next_phase": "text", "reason": "default_text_loop", "should_end": false }

  }

}

```



当 `flow.next_phase === "end"` 或 `result.is_game_over === true` 时，前端应跳转结算页。



---



### 6.4 对局结算并落库



- **Method**：`POST`

- **Path**：`/api/v1/sessions/{session_id}/settle`



响应体（节选）：



```json

{

  "code": 0,

  "message": "ok",

  "data": {

    "result": {

      "final_salary": 17800,

      "final_score": 58,

      "grade": "C",

      "title": "入门求职者",

      "breakdown": { "dq": 52, "td": 35, "wh": 70, "si": 62 }

    },

    "persist": { "saved": true, "user_id": "user_abc123", "session_id": "sess_001" }

  }

}

```



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



---



## 8. 最小联调流程



1. `POST /api/v1/sessions` 创建对局。

2. 循环调用 `POST /api/v1/sessions/{id}/text-turn` 推进回合。

3. 游戏结束后调用 `POST /api/v1/sessions/{id}/settle`。

4. 检查 `persist.saved = true`。



---



## 9. 示例 cURL



```bash

BASE_URL="http://127.0.0.1:8000"



curl -X GET "$BASE_URL/api/v1/health"



curl -X POST "$BASE_URL/api/v1/sessions" \

  -H "Content-Type: application/json" \

  -d "{\"user_id\":\"user_abc123\",\"user_name\":\"小明\"}"



curl -X POST "$BASE_URL/api/v1/sessions/sess_001/text-turn" \

  -H "Content-Type: application/json" \

  -d "{\"player_text\":\"我想了解薪资结构\"}"



curl -X POST "$BASE_URL/api/v1/sessions/sess_001/settle" \

  -H "Content-Type: application/json" \

  -d "{}"

```



---



## 10. 变更记录



- `v1`：黑客松最小可用 API，覆盖对局主链路与结算落库。

- `v1.2`：对齐双交付通道，扩展结算字段与 HR 性格元数据。

- `v1.3`：**移除全部语音链路**（`voice-turn`、WebSocket 实时通话、`speech/asr`、`speech/tts`）；仅保留文字谈判主链路。


