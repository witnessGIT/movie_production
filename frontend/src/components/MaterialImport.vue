<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api'
import type { Asset } from '../types'

const props = defineProps<{ projectId: string; assets: Asset[] }>()
const emit = defineEmits<{ changed:[] }>()
const url = ref('')
const urlLabel = ref('')
const sourceType = ref('reference')
const textLabel = ref('补充文字素材')
const text = ref('')
const status = ref('')

async function upload(event: Event) {
  if (!props.projectId) return
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (!files.length) return
  status.value = `正在上传 ${files.length} 个文件…`
  try { for (const file of files) await api.upload(props.projectId, file); status.value = '上传完成'; emit('changed') }
  catch(e) { status.value = `上传失败：${e}` }
  finally { input.value = '' }
}
async function addUrl() {
  if (!props.projectId || !url.value.trim()) return
  await api.addUrl(props.projectId, url.value.trim(), urlLabel.value.trim(), sourceType.value)
  url.value=''; urlLabel.value=''; emit('changed')
}
async function addText() {
  if (!props.projectId || !text.value.trim()) return
  await api.addText(props.projectId, textLabel.value, text.value)
  text.value=''; emit('changed')
}
function size(n?: number) { if (!n) return '—'; if (n<1024*1024) return `${(n/1024).toFixed(1)} KB`; return `${(n/1024/1024).toFixed(1)} MB` }
</script>

<template>
  <div class="settings-stack">
    <section class="grid three">
      <div class="panel import-card"><h2>本地文件</h2><p>视频、图片、音频、字幕、文本都可以先导入素材池。</p><label class="dropzone"><input type="file" multiple accept="video/*,image/*,audio/*,.srt,.vtt,.txt,.md" @change="upload" /><span>＋ 选择或拖入素材文件</span><small>大文件保存在本地 data/，不会提交 Git</small></label><div class="hint">{{ status }}</div></div>
      <div class="panel import-card"><h2>URL 素材</h2><p>登记新闻页、视频页、图片页或参考链接；后续由 SourceAdapter 处理。</p><label>URL<input v-model="url" placeholder="https://…" /></label><label>名称<input v-model="urlLabel" placeholder="可选" /></label><label>类型<select v-model="sourceType"><option value="news">新闻</option><option value="video">视频</option><option value="image">图片</option><option value="audio">音频</option><option value="reference">参考</option></select></label><button class="secondary" @click="addUrl">加入素材池</button></div>
      <div class="panel import-card"><h2>补充文字</h2><p>可加入新闻全文、采访稿、背景资料、字幕等文本。</p><label>名称<input v-model="textLabel" /></label><label>内容<textarea v-model="text" rows="7" placeholder="粘贴文本…"></textarea></label><button class="secondary" @click="addText">加入素材池</button></div>
    </section>

    <section class="panel"><div class="panel-head"><div><h2>素材池</h2><p>{{ assets.length }} 项 · 所有素材都保留来源信息</p></div></div><div v-if="!projectId" class="empty">请先创建或选择一个项目。</div><div v-else-if="!assets.length" class="empty">还没有素材。可以上传文件、添加 URL 或补充文字。</div><div v-else class="asset-table"><div class="asset-row asset-head"><span>名称</span><span>类型</span><span>来源</span><span>大小</span><span>时间</span></div><div class="asset-row" v-for="a in assets" :key="a.id"><span><strong>{{ a.label }}</strong><small>{{ a.media_type }}</small></span><span class="badge muted">{{ a.kind }}</span><span class="truncate">{{ a.source }}</span><span>{{ size(a.size_bytes) }}</span><span>{{ new Date(a.created_at).toLocaleString() }}</span></div></div></section>
  </div>
</template>
