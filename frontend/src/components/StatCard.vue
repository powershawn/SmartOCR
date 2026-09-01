<script setup lang="ts">
defineProps<{ label: string; value: string | number; helper: string; tone?: string }>()
</script>

<template>
  <article class="stat-card" :class="tone">
    <div class="stat-label">{{ label }}<span class="stat-dot"></span></div>
    <strong>{{ value }}</strong>
    <small>{{ helper }}</small>
    <div class="spark"><i v-for="n in 9" :key="n" :style="{ height: `${20 + ((n * 17) % 55)}%` }"></i></div>
  </article>
</template>

