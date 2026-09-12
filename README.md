# Movie Production

面向新闻/文字驱动的可视化视频素材检索与自动制作系统。

## 当前版本

`v0.2.0` — 可真实运行的本地视频制作 MVP。

当前已经不是纯流程占位：系统可以把文案、上传素材和用户提供的公开视频 URL 送入真实媒体分析，生成候选片段、时间线，并通过 FFmpeg 输出视频。没有素材时也会生成占位成片，保证整条流水线可验证。

## 完整流程

1. 原文导入与清洗；
2. 事实单元拆分；
3. 事实/时间核验清单；
4. 旁白与叙事规划；
5. 镜头需求规划；
6. 指定来源发现相关新闻 / 生成站内搜索入口；
7. 用户提供的公开视频 URL 可在本机通过 yt-dlp 获取；
8. FFprobe 媒体信息分析；
9. faster-whisper 语音转文字（安装时可用）；
10. PySceneDetect 镜头切分（安装时可用）；
11. 关键词 + 质量评分粗筛；
12. Ollama / LM Studio + BGE embedding 可选语义重排；
13. GPT 强模型人工交接包 / 本地模式；
14. 自动生成时间线；
15. Windows/macOS 可选本机免费 TTS 旁白；
16. SRT 字幕文件；
17. FFmpeg 生成 MP4 / MOV / WebM；
18. 成片基础 QA；
19. 前端实时显示阶段、日志、候选镜头、时间线与最终成片入口。

系统遵循：**工具优先、本地模型批量筛选、强模型只处理少量关键决策**。

## 指定素材来源

在前端 `基础设置 → 素材来源网站` 中可增加：

- `RSS / Atom`：自动读取新闻条目，并按当前文案/镜头相关度排序；
- `站内搜索模板`：地址中使用 `{query}` 占位符，例如 `https://example.com/search?q={query}`；
- `人工参考`：记录来源和授权信息，不自动抓取。

对于结构特殊、需要 JavaScript 或具有专门检索逻辑的网站，可以继续增加独立 Source Adapter。系统不会绕过 DRM、登录墙或访问控制。

## 技术栈

- Backend: Python 3.11+, FastAPI, Pydantic
- Frontend: Vue 3 + Vite + TypeScript
- Realtime: WebSocket
- Video: FFmpeg / FFprobe
- Video URL: yt-dlp（仅处理用户提供且允许获取的公开 URL）
- ASR: faster-whisper
- Scene detection: PySceneDetect
- Embedding: BGE-M3 via Ollama / LM Studio（可选）
- Local LLM: Ollama / LM Studio（可选）
- GPT: 正常登录 ChatGPT / Work 后人工交接，不把网页伪装成 API
- Browser session: Playwright（可选，仅用于用户主动打开独立登录 Profile）

## GPT 账号说明

前端中的“GPT 账号”是浏览器会话 Profile：保存账号标签、Profile 目录和交接方式，不保存密码。

系统不会用 Selenium/Playwright 自动抓取 ChatGPT 回复。强模型阶段会保存结构化交接数据，用户可在正常登录的 ChatGPT / Work 中复核候选，再继续后续制作。

## Windows 最简单安装方式

### 第一次使用

先安装：

- Git
- Python 3.11 或更高版本（安装时勾选 `Add Python to PATH`）
- Node.js LTS
- 推荐安装 FFmpeg，并确保 `ffmpeg` / `ffprobe` 在 PATH 中

然后在 PowerShell 中：

```powershell
git clone https://github.com/witnessGIT/movie_production.git
cd movie_production
.\INSTALL_WINDOWS.bat
```

安装脚本会自动：

- 创建 Python 虚拟环境；
- 安装 FastAPI 后端；
- 安装 faster-whisper、PySceneDetect、yt-dlp；
- 运行后端测试；
- 安装前端 npm 依赖；
- 运行前端生产构建；
- 检测 FFmpeg、FFprobe、yt-dlp、Ollama。

如需页面里的 GPT 独立登录窗口，再执行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -e ".[browser]"
.\.venv\Scripts\playwright.exe install chromium
```

### 以后启动

直接双击：

```text
START_WINDOWS.bat
```

启动后：

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## 使用方法

1. 打开 `基础设置`，设置视频尺寸、时长、FPS、码率、格式、字幕和旁白；
2. 可配置 Ollama / LM Studio 与素材来源网站；
3. 在 `素材库` 上传本地视频、图片、音频、文本，或者添加公开视频 URL；
4. 在 `制作台` 粘贴新闻/文案；
5. 点击 `开始制作`；
6. 页面实时显示 12 个制作阶段；
7. 候选排序完成后可以看到每个镜头的最高匹配素材和时间码；
8. 时间线生成后显示 V1 轨道；
9. FFmpeg 渲染成功后顶部出现 `查看成片`。

## 测试与 CI

GitHub Actions 每次提交都会执行：

- 前端 TypeScript + Vite 正式构建；
- 后端 pytest；
- CI 安装 FFmpeg；
- 真实 FFmpeg 渲染 smoke test；
- 文案 → 12阶段流水线 → 时间线 → `final.mp4` → QA 的端到端测试。

## 目录

```text
movie_production/
├─ backend/
│  ├─ app/
│  │  ├─ pipeline.py
│  │  ├─ media_engine.py
│  │  ├─ ranking.py
│  │  ├─ local_models.py
│  │  ├─ source_discovery.py
│  │  ├─ remote_media.py
│  │  ├─ narration.py
│  │  └─ renderer.py
│  └─ tests/
├─ frontend/
├─ docs/
├─ data/                 # 本地运行时数据，大媒体不提交 Git
├─ scripts/
├─ INSTALL_WINDOWS.bat
├─ START_WINDOWS.bat
└─ README.md
```

## 当前边界

v0.2 已经能端到端真实出片，但以下能力属于后续针对具体站点/制作风格继续增强的适配层，而不是核心流水线缺失：

- 特定新闻网站的专用搜索/页面解析 Adapter；
- 受版权或登录限制素材的授权接入；
- 强模型完全无人值守复核（当前按设计使用正常 ChatGPT 登录人工交接，或本地模型）；
- 更高级剪辑语言，如转场、动态字幕、BGM 混音、封面和复杂多轨。

核心原则：不绕过访问控制，不把背景素材冒充事件现场，所有自动步骤都允许降级并保留可追溯产物。
