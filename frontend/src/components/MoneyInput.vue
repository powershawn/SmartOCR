<script setup lang="ts">
import { ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: number | null
  currency?: string
  placeholder?: string
}>(), { currency: 'TWD', placeholder: '0' })

const emit = defineEmits<{ 'update:modelValue': [value: number | null] }>()
const display = ref('')
const focused = ref(false)

function formatted(value: number | null) {
  if (value == null || Number.isNaN(value)) return ''
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value)
}

watch(() => props.modelValue, (value) => {
  if (!focused.value) display.value = formatted(value)
}, { immediate: true })

function onFocus() {
  focused.value = true
  display.value = props.modelValue == null ? '' : String(props.modelValue)
}

function onInput(event: Event) {
  const input = event.target as HTMLInputElement
  const cleaned = input.value.replace(/,/g, '').replace(/[^\d.]/g, '')
  const [whole = '', ...decimals] = cleaned.split('.')
  display.value = decimals.length ? `${whole}.${decimals.join('').slice(0, 2)}` : whole
  const value = Number(display.value)
  emit('update:modelValue', display.value === '' || Number.isNaN(value) ? null : value)
}

function onBlur() {
  focused.value = false
  display.value = formatted(props.modelValue)
}
</script>

<template>
  <div class="money-input">
    <span>{{ currency }}</span>
    <input
      :value="display"
      type="text"
      inputmode="decimal"
      :placeholder="placeholder"
      @focus="onFocus"
      @input="onInput"
      @blur="onBlur"
    />
  </div>
</template>

