# Movie Production v0.1 Architecture

## 1. 总体原则

系统不让单一大模型包办全部工作，而是分成四层：

- TIER 0：确定性工具（FFmpeg、FFprobe、PySceneDetect、文件哈希、规则引擎）；
- TIER 1：低成本本地小模型（标签、搜索词、实体粗提取）；
- TIER 2：本地中模型/视觉模型（字幕摘要、候选镜头粗筛、图片理解）；
- TIER 3：强模型人工交接（复杂事实判断、最终叙事、Top-N 镜头复核、最终 QA）。

## 2. 数据链

```text
source_text
  -> facts.json
  -> narration.json
  -> shot_plan.json
  -> search_plan.json
  -> candidates.json
  -> clips.json
  -> verification.json
  -> timeline.json
  -> render.mp4
  -> qa.json
```

每一层都能单独重跑，后续阶段只依赖结构化文件，不依赖聊天历史。

## 3. GPT 账号模式

“GPT账号”在系统里不是用户名/密码仓库，而是浏览器会话 Profile：

```json
{
  "id": "gpt-main",
  "label": "主账号",
  "browser_profile_dir": "profiles/gpt-main",
  "handoff_mode": "manual_work"
}
```

系统可以为强模型任务生成 `AI_TASK.json`、字幕摘要、候选片段和 contact sheet。用户在正常登录的 ChatGPT/Work 中处理后，将 `AI_RESULT.json` 导回。项目不把 ChatGPT 网页模拟成隐藏 API，也不保存账户密码。

## 4. 素材等级

- S：本次事件直接现场；
- A：本次事件官方/主流来源直接画面；
- B：同人物/地点的近期相关画面；
- C：相关背景新闻素材；
- D：通用 B-roll。

评分维度：事实匹配、时间匹配、语义相关性、来源可信度、画质、镜头可用性、版权/授权风险、重复度。

## 5. 后端

FastAPI 负责：

- 设置持久化；
- 项目与素材元数据；
- 文件上传；
- 能力检测；
- 流水线任务；
- WebSocket 实时事件；
- 阶段产物 JSON。

v0.1 使用 JSON 文件持久化，便于理解与调试；数据量增大后迁移 SQLite/PostgreSQL。

## 6. 前端

Vue 3 单页控制台分四个工作区：

1. 制作台；
2. 基础设置；
3. 素材库；
4. 任务监控。

制作台优先显示过程，而不是只显示一个总进度条：阶段节点、当前工作、输入输出、日志、候选镜头和时间线都可见。

## 7. 后续适配器

`pipeline.py` 只定义阶段，不直接依赖某家站点。后续每个网站实现独立 SourceAdapter：

- search(query)；
- inspect(url)；
- transcript/metadata；
- acquire（仅在允许的情况下）；
- provenance。

这样新增站点不需要修改核心流水线。
