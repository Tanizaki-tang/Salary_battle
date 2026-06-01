<template>
  <label class="form-field">
    昵称：
    <input v-model="userName" maxlength="24" placeholder="排行榜显示用（如：小陈）" />
  </label>
  <label class="form-field">
    职位：
    <select v-model="sceneId">
      <option v-for="scene in SCENE_OPTIONS" :key="scene.sceneId" :value="scene.sceneId">
        {{ scene.label }}
      </option>
    </select>
  </label>
  <p class="form-hint">HR 面试官性格将在开局时随机分配，并在对话界面标注。</p>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { SCENE_OPTIONS, findSceneOption } from "../../constants/scenes";

export type StartSessionParams = {
  userName: string;
  sceneId: string;
  roleId: string;
};

const userName = ref("");
const sceneId = ref("scene_001");

const emit = defineEmits<{
  sceneChange: [payload: { sceneId: string }];
}>();

watch(
  sceneId,
  (value) => {
    emit("sceneChange", { sceneId: value });
  },
  { immediate: true },
);

function reset() {
  userName.value = "";
  sceneId.value = "scene_001";
}

function validate(): string | null {
  if (!userName.value.trim()) return "请填写昵称，排行榜将显示该名称";
  return null;
}

function getSessionParams(): StartSessionParams {
  const scene = findSceneOption(sceneId.value) || SCENE_OPTIONS[0];
  return {
    userName: userName.value.trim(),
    sceneId: scene.sceneId,
    roleId: scene.roleId,
  };
}

defineExpose({
  reset,
  validate,
  getSessionParams,
});
</script>

<style scoped>
.form-hint {
  margin: 0;
  font-size: 11px;
  line-height: 1.45;
  color: #888;
}
</style>
