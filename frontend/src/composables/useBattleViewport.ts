import { computed, onMounted, onUnmounted, ref } from "vue";

const PHONE_WIDTH = 375;
const PHONE_HEIGHT = 700;
const MORPH_MS = 680;

export function useBattleViewport() {
  const isExpanded = ref(false);
  const isMorphing = ref(false);
  const viewportW = ref(typeof window !== "undefined" ? window.innerWidth : PHONE_WIDTH);
  const viewportH = ref(typeof window !== "undefined" ? window.innerHeight : PHONE_HEIGHT);

  /** 全屏时按视口缩放，上限 1.05 避免卡牌区溢出 */
  const uiScale = computed(() => {
    if (!isExpanded.value) return 1;
    const hScale = viewportH.value / PHONE_HEIGHT;
    const wScale = viewportW.value / (PHONE_WIDTH * 2.2);
    return Math.min(hScale, wScale, 1.05);
  });

  function syncViewport() {
    viewportW.value = window.innerWidth;
    viewportH.value = window.innerHeight;
  }

  function setBodyLock(locked: boolean) {
    document.body.classList.toggle("battle-fullscreen-active", locked);
  }

  function setExpanded(expanded: boolean) {
    if (isMorphing.value || isExpanded.value === expanded) return;
    isMorphing.value = true;
    isExpanded.value = expanded;
    setBodyLock(expanded);
    window.setTimeout(() => {
      isMorphing.value = false;
    }, MORPH_MS);
  }

  function toggleExpand() {
    setExpanded(!isExpanded.value);
  }

  function expand() {
    setExpanded(true);
  }

  function collapse() {
    setExpanded(false);
  }

  onMounted(() => {
    syncViewport();
    window.addEventListener("resize", syncViewport);
  });

  onUnmounted(() => {
    window.removeEventListener("resize", syncViewport);
    setBodyLock(false);
  });

  return {
    isExpanded,
    isMorphing,
    uiScale,
    toggleExpand,
    expand,
    collapse,
    morphMs: MORPH_MS,
  };
}
