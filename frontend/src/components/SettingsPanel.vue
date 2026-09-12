<script setup lang="ts">
import { computed, ref } from 'vue'
import { api } from '../api'
import type { AppSettings, Capability } from '../types'

const props = defineProps<{ modelValue: AppSettings | null; capabilities: Capability[] }>()
const emit = defineEmits<{ 'update:modelValue':[AppSettings|null]; saved:[] }>()
const saving = ref(false)
const message = ref('')
const settings = computed({ get: () => props.modelValue, set: v => emit('update:modelValue', v) })

function addProfile() {
  if (!settings.value) return
  const id = `gpt-${Date.now()}`
  settings.value.gpt_profiles.push({ id, label: `GPT账号 ${settings.value.gpt_profiles.length + 1}`, browser_profile_dir: `profiles/${id}`, handoff_mode: 'manual_work', notes: '' })
  if (!settings.value.active_gpt_profile_id) settings.value.active_gpt_profile_id = id
}
function removeProfile(id: string) {
  if (!settings.value) return
  settings.value.gpt_profiles = settings.value.gpt_profiles.filter(p => p.id !== id)
  if (settings.value.active_gpt_profile_id === id) settings.value.active_gpt_profile_id = settings.value.gpt_profiles[0]?.id || null
}
function applyPreset(preset: string) {
  if (!settings.value) return
  const v = settings.value.video
  if (preset === 'landscape') Object.assign(v, { width:1920, height:1080, aspect_mode:'16:9' })
  if (preset === 'vertical') Object.assign(v, { width:1080, height:1920, aspect_mode:'9:16' })
  if (preset === 'square') Object.assign(v, { width:1080, height:1080, aspect_mode:'1:1' })
}
async function save() {
  if (!settings.value) return
  saving.value = true; message.value = ''
  try { emit('update:modelValue', await api.saveSettings(settings.value)); message.value = '设置已保存'; emit('saved') }
  catch(e) { message.value = `保存失败：${e}` }
  finally { saving.value = false }
}
</script>

<template>
  <div v-if="settings" class="settings-stack">
    <section class="panel">
      <div class="panel-head"><div><h2>GPT 会话</h2><p>只保存会话 Profile 信息，不保存密码；用于强模型人工交接</p></div><button class="secondary" @click="addProfile">＋ 添加账号配置</button></div>
      <div class="profile-list" v-if="settings.gpt_profiles.length">
        <div class="profile-card" v-for="p in settings.gpt_profiles" :key="p.id">
          <label class="radio-row"><input type="radio" v-model="settings.active_gpt_profile_id" :value="p.id" /><span>当前账号</span></label>
          <label>显示名称<input v-model="p.label" /></label>
          <label>浏览器 Profile 目录<input v-model="p.browser_profile_dir" placeholder="profiles/gpt-main" /></label>
          <label>交接方式<select v-model="p.handoff_mode"><option value="manual_work">ChatGPT Work</option><option value="manual_chat">普通 ChatGPT 会话</option></select></label>
          <label>备注<input v-model="p.notes" placeholder="例如：Plus 主账号" /></label>
          <button class="danger-text" @click="removeProfile(p.id)">删除配置</button>
        </div>
      </div>
      <div v-else class="empty">还没有 GPT 会话配置。添加后可为 TIER 3 任务指定使用哪个已登录账号。</div>
    </section>

    <section class="panel">
      <div class="panel-head"><div><h2>视频规格</h2><p>成片目标与时间线长度都使用这里的参数</p></div><div class="preset-buttons"><button class="chip" @click="applyPreset('landscape')">横屏 16:9</button><button class="chip" @click="applyPreset('vertical')">竖屏 9:16</button><button class="chip" @click="applyPreset('square')">方形 1:1</button></div></div>
      <div class="form-grid four">
        <label>宽度<input type="number" min="320" max="7680" v-model.number="settings.video.width" /></label>
        <label>高度<input type="number" min="240" max="4320" v-model.number="settings.video.height" /></label>
        <label>FPS<input type="number" min="12" max="120" v-model.number="settings.video.fps" /></label>
        <label>目标时长（秒）<input type="number" min="5" max="7200" v-model.number="settings.video.target_duration_sec" /></label>
        <label>码率<input v-model="settings.video.bitrate" /></label>
        <label>格式<select v-model="settings.video.format"><option>mp4</option><option>mov</option><option>webm</option></select></label>
        <label>画幅<select v-model="settings.video.aspect_mode"><option>16:9</option><option>9:16</option><option>1:1</option><option>custom</option></select></label>
        <label class="check"><input type="checkbox" v-model="settings.video.subtitle_enabled" />生成字幕</label>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head"><div><h2>模型分层</h2><p>低成本任务先本地处理，强模型只看压缩后的候选</p></div></div>
      <div class="form-grid three">
        <label>TIER 1 Provider<select v-model="settings.models.tier1_provider"><option>ollama</option><option>lmstudio</option><option>disabled</option></select></label>
        <label>TIER 1 模型<input v-model="settings.models.tier1_model" /></label>
        <label>Embedding<input v-model="settings.models.embedding_model" /></label>
        <label>TIER 2 Provider<select v-model="settings.models.tier2_provider"><option>ollama</option><option>lmstudio</option><option>disabled</option></select></label>
        <label>TIER 2 模型<input v-model="settings.models.tier2_model" /></label>
        <label>强模型<select v-model="settings.models.strong_model_mode"><option value="chatgpt_handoff">ChatGPT 人工交接</option><option value="local_only">只用本地模型</option></select></label>
        <label>每镜头送强模型的候选数<input type="number" min="1" max="20" v-model.number="settings.max_candidate_clips_per_shot" /></label>
        <label class="check"><input type="checkbox" v-model="settings.keep_intermediate_files" />保留中间产物</label>
      </div>
      <div class="capabilities-inline"><span v-for="c in capabilities" :key="c.id" :class="['badge', c.available?'ok':'muted']">{{ c.label }} {{ c.available?'✓':'未就绪' }}</span></div>
    </section>

    <div class="savebar"><span>{{ message }}</span><button class="primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存全部设置' }}</button></div>
  </div>
</template>
