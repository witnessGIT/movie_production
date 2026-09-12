<script setup lang="ts">
import type { TimelineSegment } from '../types'
const props = defineProps<{ segments: TimelineSegment[]; duration: number }>()
function left(s: TimelineSegment){ return `${Math.max(0, s.start/props.duration*100)}%` }
function width(s: TimelineSegment){ return `${Math.max(2, (s.end-s.start)/props.duration*100)}%` }
function time(n:number){ const m=Math.floor(n/60); const s=Math.floor(n%60).toString().padStart(2,'0'); return `${m}:${s}` }
</script>
<template>
  <div class="timeline-wrap">
    <div class="time-ruler"><span v-for="i in 5" :key="i" :style="{left:((i-1)/4*100)+'%'}">{{ time((i-1)/4*duration) }}</span></div>
    <div class="track"><div class="track-label">V1</div><div class="track-lane"><div v-for="s in segments" :key="s.id" class="clip" :style="{left:left(s),width:width(s)}"><span>{{ s.label }}</span><small>{{ time(s.start) }}–{{ time(s.end) }}</small></div><div v-if="!segments.length" class="timeline-empty">等待时间线阶段生成</div></div></div>
    <div class="track muted-track"><div class="track-label">A1</div><div class="track-lane"><div class="audio-placeholder">旁白 / 环境音 / BGM</div></div></div>
  </div>
</template>
