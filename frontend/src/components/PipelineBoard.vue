<script setup lang="ts">
import type { Job } from '../types'
defineProps<{ job: Job | null; compact?: boolean }>()
</script>

<template>
  <div v-if="!job" class="empty pipeline-empty">尚未开始制作。保存文案并点击“开始制作”。</div>
  <div v-else :class="['pipeline', {compact}]">
    <div v-for="(stage,index) in job.stages" :key="stage.id" class="stage" :data-state="stage.state">
      <div class="stage-index"><span v-if="stage.state==='done'">✓</span><span v-else>{{ index+1 }}</span></div>
      <div class="stage-body"><div class="stage-top"><strong>{{ stage.label }}</strong><small>{{ stage.progress }}%</small></div><div class="bar"><i :style="{width: stage.progress+'%'}"></i></div><p>{{ stage.detail || (stage.state==='pending'?'等待上一步':'处理中') }}</p><small v-if="stage.artifact" class="artifact">产物：{{ stage.artifact }}</small></div>
    </div>
  </div>
</template>
