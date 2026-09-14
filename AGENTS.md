# AGENTS.md

## 普通 Agent 工作规则

本仓库必须让没有视频播放能力的普通 Agent 也能完成语义检查。Agent 不得声称自己播放、观看或听取了无法访问的视频。

### 成片检查入口

每次渲染后，项目自动生成：

- `qa.json`：程序完成的技术检查与最终交付状态；
- `agent_review.json`：逐镜头语义检查任务；
- `agent_review_frames/`：每个镜头开头、中间、结尾三张关键帧；
- `agent_review_result.json`：普通 Agent 必须填写的结构化结果。

### 普通 Agent 的检查步骤

1. 先读 `qa.json`，确认 `technical_ok=true`。若为 false，优先修复技术问题，不做语义通过声明。
2. 读 `agent_review.json`，逐个镜头查看列出的三张关键帧。
3. 将画面与 `voiceover_or_label`、`asset_id`、来源路径和时间码比较。
4. 按 `result_schema` 创建 `agent_review_result.json`。
5. 每项只能填写 `pass`、`fail` 或 `needs_human_review`。
6. 遇到人物、地点、事件、时间背景不一致，必须填 `fail` 并写依据。
7. 关键帧无法证明动态过程、语气、音画同步或细节时，必须填 `needs_human_review`，不得猜测。
8. 重新运行 QA。只有 `delivery_ready=true` 才能把成片标记为可交付。

### 禁止事项

- 不得把候选分数、文件名或程序技术检查当作语义正确的证据；
- 不得在没有查看全部关键帧时批量填写 `pass`；
- 不得把 `technical_ok=true` 写成“视频全部检查通过”；
- 不得删除失败、升级人工或关键帧提取错误记录。
