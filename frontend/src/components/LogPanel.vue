<script setup lang="ts">
defineProps<{ logs: string[]; tall?: boolean }>()
</script>
<template><div :class="['logbox',{tall}]"><div v-if="!logs.length" class="log-empty">等待任务日志…</div><div v-for="(line,i) in logs" :key="i" class="logline"><span>{{ String(i+1).padStart(2,'0') }}</span>{{ line }}</div></div></template>
