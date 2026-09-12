<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api, jobSocket } from './api'
import type { AppSettings, Asset, Capability, Job, Project } from './types'
import SettingsPanel from './components/SettingsPanel.vue'
import MaterialImport from './components/MaterialImport.vue'
import PipelineBoard from './components/PipelineBoard.vue'
import TimelinePreview from './components/TimelinePreview.vue'
import LogPanel from './components/LogPanel.vue'

const tabs = ['制作台', '基础设置', '素材库', '任务监控'] as const
const tab = ref<(typeof tabs)[number]>('制作台')
const projects = ref<Project[]>([])
const currentId = ref('')
const title = ref('')
const sourceText = ref('')
const settings = ref<AppSettings | null>(null)
const capabilities = ref<Capability[]>([])
const assets = ref<Asset[]>([])
const job = ref<Job | null>(null)
const rankArtifact = ref<any | null>(null)
const renderArtifact = ref<any | null>(null)
const busy = ref(false)
const error = ref('')
let socket: WebSocket | null = null

const current = computed(() => projects.value.find(p => p.id === currentId.value) || null)
const overall = computed(() => !job.value ? 0 : Math.round(job.value.stages.reduce((s, x) => s + x.progress, 0) / job.value.stages.length))
const topCandidates = computed(() => (rankArtifact.value?.ranked || []).slice(0, 6))

async function refresh() {
  ;[projects.value, settings.value, capabilities.value] = await Promise.all([api.projects(), api.settings(), api.capabilities()])
  if (!currentId.value && projects.value.length) await selectProject(projects.value[0].id)
}

async function loadOutputs(jobId: string) {
  if (!currentId.value) return
  rankArtifact.value = null
  renderArtifact.value = null
  try { rankArtifact.value = await api.artifact(currentId.value, jobId, 'rank') } catch {}
  try { renderArtifact.value = await api.artifact(currentId.value, jobId, 'render') } catch {}
}

async function selectProject(id: string) {
  currentId.value = id
  const p = projects.value.find(x => x.id === id)
  title.value = p?.title || ''
  sourceText.value = p?.source_text || ''
  assets.value = await api.assets(id)
  const jobs = await api.jobs(id)
  job.value = jobs[0] || null
  rankArtifact.value = null
  renderArtifact.value = null
  if (job.value) await loadOutputs(job.value.id)
}

async function newProject() {
  const p = await api.createProject('新视频项目', '')
  await refresh()
  await selectProject(p.id)
}

async function saveProject() {
  if (!currentId.value) return
  busy.value = true
  try { await api.updateProject(currentId.value, title.value || '未命名项目', sourceText.value); await refresh() }
  catch (e) { error.value = String(e) }
  finally { busy.value = false }
}

async function run() {
  if (!currentId.value) return
  await saveProject()
  rankArtifact.value = null
  renderArtifact.value = null
  const createdJob = await api.startJob(currentId.value)
  job.value = createdJob
  if (socket) socket.close()
  socket = jobSocket(createdJob.id)
  socket.onmessage = async event => {
    const data = JSON.parse(event.data)
    if (data.type === 'snapshot') {
      job.value = data.job
      return
    }
    const active = job.value
    if (!active) return
    if (data.type === 'stage') {
      const i = active.stages.findIndex(s => s.id === data.stage.id)
      if (i >= 0) active.stages[i] = data.stage
      if (data.stage.id === 'rank' && data.stage.state === 'done') {
        try { rankArtifact.value = await api.artifact(currentId.value, active.id, 'rank') } catch {}
      }
      if (data.stage.id === 'render' && data.stage.state === 'done') {
        try { renderArtifact.value = await api.artifact(currentId.value, active.id, 'render') } catch {}
      }
    }
    if (data.type === 'log') active.logs.push(data.message)
    if (data.type === 'job') {
      active.state = data.state
      if (data.timeline) active.timeline = data.timeline
      if (data.state === 'done') await loadOutputs(active.id)
    }
  }
}

async function assetChanged() {
  if (currentId.value) assets.value = await api.assets(currentId.value)
  projects.value = await api.projects()
}

onMounted(() => refresh().catch(e => error.value = String(e)))
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark">MP</div><div><strong>Movie Production</strong><small>AI 视频制作控制台</small></div></div>
      <nav><button v-for="item in tabs" :key="item" :class="{active: tab===item}" @click="tab=item">{{ item }}</button></nav>
      <div class="project-list">
        <div class="section-title"><span>项目</span><button class="icon-button" @click="newProject">＋</button></div>
        <button v-for="p in projects" :key="p.id" class="project-button" :class="{selected:p.id===currentId}" @click="selectProject(p.id)"><span>{{ p.title }}</span><small>{{ p.asset_count }} 素材</small></button>
      </div>
      <div class="sidebar-foot"><span class="dot online"></span> Backend v0.2</div>
    </aside>

    <main class="main">
      <header class="topbar">
        <div><h1>{{ tab }}</h1><p v-if="current">{{ current.title }}</p></div>
        <div class="top-actions">
          <span v-if="job" class="progress-label">总进度 {{ overall }}%</span>
          <a v-if="job && renderArtifact?.output" class="secondary" :href="api.outputUrl(currentId, job.id)" target="_blank">▶ 查看成片</a>
          <button class="primary" :disabled="!currentId || job?.state==='running'" @click="run">▶ 开始制作</button>
        </div>
      </header>

      <div v-if="error" class="error-banner">{{ error }}</div>

      <template v-if="tab==='制作台'">
        <section class="grid two">
          <div class="panel source-panel">
            <div class="panel-head"><div><h2>新闻 / 文案输入</h2><p>这里是整个制作任务的事实来源</p></div><button class="secondary" :disabled="busy" @click="saveProject">保存</button></div>
            <label>项目名称<input v-model="title" placeholder="视频项目名称" /></label>
            <label>原文<textarea v-model="sourceText" rows="14" placeholder="粘贴新闻、文章或完整文案……"></textarea></label>
            <div class="stats"><span>{{ sourceText.length }} 字</span><span>{{ assets.length }} 个素材</span><span>{{ settings?.video.target_duration_sec || 60 }} 秒目标</span></div>
          </div>
          <div class="panel status-panel">
            <div class="panel-head"><div><h2>制作状态</h2><p>工具先筛选，强模型只处理关键决策</p></div><span class="state-pill" :data-state="job?.state || 'idle'">{{ job?.state || '未开始' }}</span></div>
            <PipelineBoard :job="job" compact />
          </div>
        </section>

        <section class="panel">
          <div class="panel-head"><div><h2>候选镜头</h2><p>媒体分析和相关性排序完成后显示每个镜头的 Top 候选</p></div></div>
          <div v-if="topCandidates.length" class="cap-grid">
            <div v-for="item in topCandidates" :key="item.shot?.shot" class="cap">
              <div><strong>镜头 {{ item.shot?.shot }} · {{ item.shot?.voiceover?.slice(0, 30) }}</strong><small v-if="item.candidates?.[0]">素材 {{ item.candidates[0].asset_id }} · 匹配 {{ Math.round((item.candidates[0].score || 0)*100) }}% · {{ item.candidates[0].start }}–{{ item.candidates[0].end }}s</small><small v-else>没有可用候选</small></div>
            </div>
          </div>
          <div v-else class="empty">等待“候选片段粗筛”完成</div>
        </section>

        <section class="panel"><div class="panel-head"><div><h2>时间线预览</h2><p>时间线使用真实素材片段；没有素材时自动生成补位镜头</p></div></div><TimelinePreview :segments="job?.timeline || []" :duration="settings?.video.target_duration_sec || 60" /></section>
        <section class="grid two"><div class="panel"><div class="panel-head"><h2>最近日志</h2></div><LogPanel :logs="job?.logs || []" /></div><div class="panel"><div class="panel-head"><h2>本机能力</h2></div><div class="cap-grid"><div v-for="c in capabilities" :key="c.id" class="cap"><span :class="['dot', c.available?'online':'offline']"></span><div><strong>{{ c.label }}</strong><small>{{ c.tier }} · {{ c.detail }}</small></div></div></div></div></section>
      </template>

      <SettingsPanel v-else-if="tab==='基础设置'" v-model="settings" :capabilities="capabilities" @saved="refresh" />
      <MaterialImport v-else-if="tab==='素材库'" :project-id="currentId" :assets="assets" @changed="assetChanged" />
      <template v-else><section class="panel"><div class="panel-head"><div><h2>流水线监控</h2><p>每个阶段独立显示状态、进度与产物路径</p></div></div><PipelineBoard :job="job" /></section><section class="panel"><div class="panel-head"><h2>完整日志</h2></div><LogPanel :logs="job?.logs || []" tall /></section></template>
    </main>
  </div>
</template>
