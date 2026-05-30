<template>
  <div
    class="speech-wrap"
    :class="[`side-${side}`, `entrance-${entrance}`, { typing, urgent: isUrgent }]"
    :style="{ '--bubble-scale': scale }"
  >
    <div v-if="typing" class="speech-bubble speech-bubble-typing" aria-label="对方正在输入">
      <span /><span /><span />
    </div>
    <div v-else class="speech-bubble" :key="`${side}-${text}`">
      <p class="speech-text">{{ text }}</p>
      <span class="speech-tail" aria-hidden="true" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { BubbleEntrance } from "../../types/bubbleEntrance";

withDefaults(
  defineProps<{
    side: "hr" | "player";
    text?: string;
    entrance?: BubbleEntrance;
    scale?: number;
    typing?: boolean;
    isUrgent?: boolean;
  }>(),
  {
    text: "",
    entrance: "fade",
    scale: 1,
    typing: false,
    isUrgent: false,
  },
);
</script>

<style scoped>
.speech-wrap {
  --bubble-scale: 1;
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
}

.side-hr {
  justify-content: flex-start;
}

.side-player {
  justify-content: flex-end;
  flex: 1;
  min-width: 0;
}

.speech-bubble {
  position: relative;
  max-width: min(420px, 38vw);
  padding: calc(12px * var(--bubble-scale)) calc(16px * var(--bubble-scale));
  border-radius: calc(14px * var(--bubble-scale));
  font-size: calc(15px * var(--bubble-scale));
  line-height: 1.55;
  word-break: break-word;
  overflow-wrap: anywhere;
  box-shadow:
    0 calc(10px * var(--bubble-scale)) calc(28px * var(--bubble-scale)) rgba(0, 0, 0, 0.28),
    inset 0 1px 0 rgba(255, 255, 255, 0.12);
}

.side-hr .speech-bubble {
  background: rgba(255, 255, 255, 0.96);
  color: #1a1a1a;
  border-top-left-radius: calc(4px * var(--bubble-scale));
}

.side-player .speech-bubble {
  background: linear-gradient(135deg, #00c2a2, #00a88d);
  color: #fff;
  border-top-right-radius: calc(4px * var(--bubble-scale));
}

.speech-text {
  margin: 0;
}

.speech-tail {
  position: absolute;
  top: calc(18px * var(--bubble-scale));
  width: calc(12px * var(--bubble-scale));
  height: calc(12px * var(--bubble-scale));
  transform: rotate(45deg);
}

.side-hr .speech-tail {
  left: calc(-5px * var(--bubble-scale));
  background: rgba(255, 255, 255, 0.96);
}

.side-player .speech-tail {
  right: calc(-5px * var(--bubble-scale));
  background: #00b896;
}

.speech-bubble-typing {
  display: flex;
  align-items: center;
  gap: calc(5px * var(--bubble-scale));
  min-width: calc(52px * var(--bubble-scale));
  min-height: calc(20px * var(--bubble-scale));
}

.speech-bubble-typing span {
  width: calc(7px * var(--bubble-scale));
  height: calc(7px * var(--bubble-scale));
  border-radius: 50%;
  background: #b7b7b7;
  animation: dotPulse 1.1s infinite ease-in-out;
}

.speech-bubble-typing span:nth-child(2) { animation-delay: 0.15s; }
.speech-bubble-typing span:nth-child(3) { animation-delay: 0.3s; }

@keyframes dotPulse {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

/* 浮现 */
.entrance-fade .speech-bubble {
  animation: bubbleFadeIn 0.55s cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes bubbleFadeIn {
  from {
    opacity: 0;
    transform: translateY(calc(12px * var(--bubble-scale))) scale(0.92);
    filter: blur(calc(4px * var(--bubble-scale)));
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
    filter: blur(0);
  }
}

/* 重重砸下 */
.entrance-slam .speech-bubble {
  animation: bubbleSlam 0.62s cubic-bezier(0.22, 1.12, 0.36, 1) both;
}

@keyframes bubbleSlam {
  0% {
    opacity: 0;
    transform: translateY(calc(-120px * var(--bubble-scale))) scale(1.08) rotate(-2deg);
  }
  55% {
    opacity: 1;
    transform: translateY(calc(6px * var(--bubble-scale))) scale(0.98) rotate(0.5deg);
  }
  72% {
    transform: translateY(calc(-3px * var(--bubble-scale))) scale(1.01);
  }
  100% {
    transform: translateY(0) scale(1) rotate(0);
  }
}

.entrance-slam .speech-bubble::after {
  content: "";
  position: absolute;
  inset: calc(-4px * var(--bubble-scale));
  border-radius: inherit;
  pointer-events: none;
  animation: slamFlash 0.62s ease both;
}

@keyframes slamFlash {
  0%, 100% { box-shadow: none; opacity: 0; }
  45% {
    opacity: 1;
    box-shadow: 0 0 calc(24px * var(--bubble-scale)) rgba(255, 71, 87, 0.35);
  }
}

/* 快速滑出 */
.entrance-slide.side-hr .speech-bubble {
  animation: bubbleSlideHr 0.42s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.entrance-slide.side-player .speech-bubble {
  animation: bubbleSlidePlayer 0.42s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes bubbleSlideHr {
  from {
    opacity: 0;
    transform: translateX(calc(-72px * var(--bubble-scale)));
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes bubbleSlidePlayer {
  from {
    opacity: 0;
    transform: translateX(calc(72px * var(--bubble-scale)));
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>
