[OPEN]

# BGM 没有正常播放（bgm-not-playing）

## Symptoms
- 普通阶段/打牌阶段 BGM 未播放或偶发播放

## Expected
- 普通阶段循环播放 `普通阶段.mp3`
- 进入卡牌阶段淡入 `打牌阶段.mp3`，退出淡回普通阶段

## Hypotheses
- H1: 浏览器自动播放策略导致 `audio.play()` 被拒绝（NotAllowedError），unlock 逻辑未触发或触发时机不对
- H2: 音频资源 URL 404/500（后端未挂载 /resources 或服务未重启），导致 audio error
- H3: URL 编码/路径字符（`music&effect`、中文文件名）导致请求失败或被服务器解析异常
- H4: 音量淡入逻辑未执行/被中断，导致 audio 一直处于 volume=0
- H5: 阶段切换时 stop/play 竞态导致刚 play 又 pause（isExpanded 监听/enterCardPhase）

## Evidence Plan
- 前端上报：unlock 触发、audio.play 结果、audio 事件（canplaythrough/playing/error）、音量变化、当前阶段
- 后端确认：/resources 路由是否存在且可访问

## Runs
- pre:
  - http://127.0.0.1:8000/resources/music&effect/普通阶段.mp3 返回 404（/resources 未挂载）
  - backend/app/main.py 里 resources_dir 指向上级目录错误：parents[3] -> D:\School\HackSong（resources 不存在）
- post: pending
