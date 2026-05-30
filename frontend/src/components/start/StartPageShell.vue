<template>
  <section class="page-root">
    <div class="phone-shell">
      <div class="phone-notch" />
      <div class="status-bar">
        <span>9:41</span>
        <span>📶 🔋</span>
      </div>

      <div class="start-screen">
        <header class="start-header">
          <p class="start-kicker">Salary Battle</p>
          <h1 class="start-title">劳资拉扯模拟器</h1>
          <div class="start-meta">
            <img class="start-avatar" :src="bossAvatarUrl" alt="HR" />
            <div>
              <p class="start-hr-name">{{ name }}</p>
              <p class="start-hr-sub">{{ company }} · {{ tagline }}</p>
            </div>
          </div>
        </header>

        <aside class="rules-box" aria-label="玩法说明">
          <h2 class="rules-title">📖 玩法说明</h2>
          <ol class="rules-list">
            <li>
              <strong>文字谈判</strong>：与 HR 自由对话，争取更高 offer；注意满意度与话术陷阱。
            </li>
            <li>
              <strong>卡牌决战</strong>：HR 耐心降至阈值后自动进入横屏卡牌阶段，倒计时内六选一策略牌。
            </li>
            <li>
              <strong>四维目标</strong>：提升 💰薪资、⏰工时约定、🛡️保障，同时别让 😊满意度 归零。
            </li>
            <li>
              <strong>结束方式</strong>：主动接受 offer、谈崩，或第 8 轮强制结算。
            </li>
          </ol>
          <p class="rules-foot">正式版：仅选择职位，HR 性格随机 · 满意度达标后进入卡牌阶段</p>
        </aside>

        <div class="selectors">
          <slot />
        </div>

        <p v-if="error" class="error">{{ error }}</p>

        <div class="start-actions">
          <button type="button" class="btn-secondary" @click="$emit('reset')">重置</button>
          <button type="button" class="btn-primary" :disabled="loading" @click="$emit('accept')">
            {{ loading ? "创建对局中…" : "开始谈判" }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { bossAvatarUrl } from "../../assets/avatars";

defineProps<{
  name: string;
  company?: string;
  tagline: string;
  loading?: boolean;
  error?: string;
}>();

defineEmits<{
  accept: [];
  reset: [];
}>();
</script>

<style scoped>
.page-root {
  width: 375px;
  height: 700px;
}

.phone-shell {
  width: 100%;
  height: 100%;
  border-radius: 32px;
  overflow: hidden;
  position: relative;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), 0 0 0 2px #1a1a1a;
  background: #f5f7fa;
}

.phone-notch {
  position: absolute;
  top: 8px;
  left: 50%;
  transform: translateX(-50%);
  width: 100px;
  height: 24px;
  background: #1a1a1a;
  border-radius: 0 0 16px 16px;
  z-index: 10;
}

.status-bar {
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  font-size: 11px;
  font-weight: 600;
  color: #333;
  flex-shrink: 0;
  background: #fff;
  border-bottom: 1px solid #eee;
}

.start-screen {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 14px 16px 18px;
  overflow-y: auto;
  gap: 12px;
}

.start-header {
  padding-top: 4px;
}

.start-kicker {
  margin: 0;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #00a88d;
}

.start-title {
  margin: 4px 0 0;
  font-size: 22px;
  font-weight: 800;
  color: #1a1a2e;
  line-height: 1.2;
}

.start-meta {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.start-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.start-hr-name {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #1a1a2e;
}

.start-hr-sub {
  margin: 2px 0 0;
  font-size: 11px;
  color: #666;
  line-height: 1.35;
}

.rules-box {
  padding: 12px 14px;
  border-radius: 14px;
  background: linear-gradient(135deg, #0a1628 0%, #12243d 100%);
  color: rgba(255, 255, 255, 0.92);
  box-shadow: 0 8px 24px rgba(10, 22, 40, 0.18);
}

.rules-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 700;
}

.rules-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 6px;
  font-size: 11px;
  line-height: 1.45;
  color: rgba(255, 255, 255, 0.82);
}

.rules-list strong {
  color: #7bed9f;
  font-weight: 700;
}

.rules-foot {
  margin: 10px 0 0;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
  font-size: 10px;
  color: rgba(255, 255, 255, 0.55);
}

.selectors {
  display: grid;
  gap: 8px;
}

.start-actions {
  margin-top: auto;
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 10px;
  padding-top: 4px;
}

.btn-primary,
.btn-secondary {
  height: 44px;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.btn-primary {
  background: linear-gradient(135deg, #00c2a2, #00a88d);
  color: #fff;
  box-shadow: 0 6px 16px rgba(0, 194, 162, 0.35);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #fff;
  color: #666;
  border: 1px solid #ddd;
}

.error {
  margin: 0;
  color: #e74c3c;
  font-size: 12px;
  text-align: center;
}
</style>

<style scoped>
:deep(.form-field) {
  font-size: 12px;
  color: #333;
  display: grid;
  gap: 4px;
}

:deep(.form-field select),
:deep(.form-field input) {
  height: 36px;
  border-radius: 10px;
  border: 1px solid #ddd;
  background: #fff;
  color: #1a1a2e;
  padding: 0 10px;
  outline: none;
}

:deep(.form-field input:focus),
:deep(.form-field select:focus) {
  border-color: #00c2a2;
  box-shadow: 0 0 0 2px rgba(0, 194, 162, 0.15);
}

:deep(.form-field input::placeholder) {
  color: #aaa;
}
</style>
