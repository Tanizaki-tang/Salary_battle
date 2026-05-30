# 多 Agent 全局分工与文件协作规范

本文件用于约束两个编程 Agent（下称 `Agent-A`、`Agent-B`）并行工作时的文件边界，避免同时改同一脚本。

## 1. 总原则（强制）

- 同一时间，一个文件只能被一个 Agent 持有并修改。
- 任何跨边界修改，必须先在会话里声明“移交文件”并得到确认后再动手。
- 禁止“顺手修一下”对方边界文件；需要修复时走移交流程。
- 单个任务结束后，先完成本边界自检，再交给对方继续。

## 2. 固定分工（当前版本）

### Agent-A 负责（后端核心 Agent 链路）

- `backend/app/orchestrators/game_flow_orchestrator.py`
- `backend/app/modules/agent/**`
- `backend/app/modules/flow_controller/phase_policy.py`
- `backend/app/modules/flow_controller/phase_router.py`
- `backend/app/contracts/flow_contract.py`
- `backend/app/contracts/voice_battle_contract.py`
- `backend/app/shared_types/game_types.py`
- `backend/app/api/session_routes.py`

### Agent-B 负责（语音实现/前端/文档/测试）

- `backend/app/modules/voice_battle/speech_gateway.py`
- `backend/app/modules/voice_battle/voice_battle_engine.py`
- `backend/app/service/llm_service.py`
- `backend/app/prompt/**`
- `frontend/**`
- `develop_documents/**`
- `README.md`
- `backend/scripts/**`（除非明确指派给 Agent-A）

## 3. 共享但需审批的文件

以下文件允许两方触达，但每次修改前必须先声明持有者：

- `backend/app/main.py`
- `backend/requirements.txt`
- `.env.example`
- `Dockerfile`

## 4. 文件移交流程（严格执行）

1) 当前持有者在会话中发：`[RELEASE] <file_path>`  
2) 接手方在会话中发：`[CLAIM] <file_path>`  
3) 接手方修改完成后发：`[DONE] <file_path>`  

未完成 `RELEASE/CLAIM` 前，另一方不得编辑该文件。

## 5. 提交前冲突检查清单

- 检查最近改动是否跨出本 Agent 负责目录。
- 检查是否出现同一文件被两方同时提交的迹象。
- 运行本边界最小验证：
  - 后端链路改动：至少跑 `health -> sessions -> text-turn/voice-turn -> settle`
  - 前端链路改动：至少跑路由流转与构建
- 输出“本次改动文件清单”，方便对方继续。

## 6. 临时优先级（本轮重构）

- 优先保证 `HR Agent` 主链路稳定（Agent-A）
- 并行推进语音真实化与提示词迭代（Agent-B）
- 任何会影响 API 入参/出参的改动，必须先同步双方再落地

---

如需调整分工，以“追加小节”方式更新本文件，不要覆盖原规则。
