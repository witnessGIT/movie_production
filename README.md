# Movie Production

面向新闻/文字驱动的视频素材检索与自动制作系统。

## 当前版本

`v0.1.0` — 可视化制作控制台与完整流水线骨架。

## 核心目标

输入新闻、文章或文案后，系统按以下链路工作：

1. 原文导入与清洗；
2. 新闻事实解析与结构化；
3. 叙事/旁白规划；
4. 镜头需求规划；
5. 指定站点素材检索；
6. 视频字幕/音频/镜头解析；
7. 候选片段粗筛、语义排序与高级复核；
8. 来源、时间、事实、重复与画质检查；
9. 旁白、字幕、时间线生成；
10. FFmpeg 渲染；
11. 成片质量检查。

系统遵循：**工具优先、本地模型批量筛选、强模型只处理关键决策**。

## 技术栈

- Backend: Python 3.11+, FastAPI, Pydantic, SQLite
- Frontend: Vue 3 + Vite + TypeScript
- Realtime: WebSocket
- Video: FFmpeg / FFprobe
- ASR: faster-whisper（可选）
- Scene detection: PySceneDetect（可选）
- Embedding: BGE-M3 via Ollama/LM Studio（可选）
- Local LLM: Ollama/LM Studio（可选）
- Browser automation: Playwright（仅用于允许的公开网页/用户主动登录工作流，不保存密码）

## GPT 账号说明

本项目不把 ChatGPT 网页当作隐藏 API。前端中的“GPT 账号”是**浏览器会话配置**：保存账号标签、浏览器配置目录和任务交接方式，不保存密码。强模型任务可打包为 `AI_TASK.json` + 候选截图/字幕，供用户在正常登录的 ChatGPT/Work 会话中处理，再把结果导回系统。

## 启动

### 1. 后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8000
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

默认：

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

## 目录

```text
movie_production/
├─ backend/
├─ frontend/
├─ docs/
├─ data/                 # 本地运行时创建，不提交大素材
├─ scripts/
├─ .gitignore
└─ README.md
```

## 当前界面

前端分为四个主要区域：

- **制作台**：从输入文本到成片的全过程可视化；
- **基础设置**：GPT会话、本地模型、视频尺寸、时长、分辨率、FPS、字幕等；
- **素材库**：上传视频/图片/音频、URL和文本素材；
- **任务监控**：每个流水线阶段、进度、日志和生成物。

## 开发原则

- 大视频文件不提交 Git；
- 每个素材保留来源、时间、版权/授权备注和哈希；
- 所有 AI 步骤都可替换 provider；
- 强模型调用前先通过工具/本地模型压缩候选集；
- 每个流水线阶段都能单独重跑，不必整条重新执行；
- 前端能看到输入、阶段状态、输出、错误和下一步动作。
