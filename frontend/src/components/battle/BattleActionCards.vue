<template>
  <div class="action-cards" role="toolbar" aria-label="谈判策略卡牌">
    <button
      v-for="card in PLAYER_ACTION_CARDS"
      :key="card.id"
      type="button"
      class="action-card"
      :class="{ active: selectedId === card.id, disabled }"
      :disabled="disabled"
      :title="card.desc"
      @click="$emit('select', card)"
    >
      <span class="action-emoji">{{ card.emoji }}</span>
      <span class="action-label">{{ card.label }}</span>
      <span class="action-desc">{{ card.desc }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { PLAYER_ACTION_CARDS, type PlayerActionCard } from "../../config/battlePlayerActions";

defineProps<{
  disabled?: boolean;
  selectedId?: PlayerActionCard["id"] | null;
}>();

defineEmits<{
  select: [card: PlayerActionCard];
}>();
</script>

<style scoped>
.action-cards {
  width: min(100%, 300px);
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.action-card {
  appearance: none;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.05);
  border-radius: 14px;
  padding: 12px 10px 11px;
  color: #fff;
  cursor: pointer;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-height: 88px;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    background 0.18s ease,
    box-shadow 0.18s ease;
}

.action-card:not(:disabled):hover {
  transform: translateY(-2px);
  border-color: rgba(0, 194, 162, 0.55);
  background: rgba(0, 194, 162, 0.12);
  box-shadow: 0 8px 24px rgba(0, 194, 162, 0.15);
}

.action-card:not(:disabled):active {
  transform: translateY(0) scale(0.98);
}

.action-card.active {
  border-color: rgba(0, 194, 162, 0.85);
  background: rgba(0, 194, 162, 0.18);
  box-shadow: 0 0 0 1px rgba(0, 194, 162, 0.35), 0 10px 28px rgba(0, 194, 162, 0.2);
}

.action-card.disabled,
.action-card:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
}

.action-emoji {
  font-size: 22px;
  line-height: 1;
}

.action-label {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.action-desc {
  font-size: 10px;
  line-height: 1.35;
  color: rgba(255, 255, 255, 0.62);
}
</style>
