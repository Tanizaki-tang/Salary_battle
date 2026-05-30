<template>
  <label class="form-field">
    昵称：
    <input v-model="userName" maxlength="24" placeholder="请输入你的名字（如：小陈）" />
  </label>
  <label class="form-field">
    角色：
    <select v-model="roleId">
      <option value="role_backend">后端开发</option>
      <option value="role_product">产品经理</option>
      <option value="role_sales">销售</option>
    </select>
  </label>
  <label class="form-field">
    场景：
    <select v-model="sceneId">
      <option v-for="scene in SCENE_OPTIONS" :key="scene.sceneId" :value="scene.sceneId">
        {{ scene.sceneId }} {{ scene.label }}
      </option>
    </select>
  </label>
  <label class="form-field">
    HR人格：
    <select v-model="hrPersonalityId">
      <option v-for="p in personalities" :key="p.personality_id" :value="p.personality_id">
        {{ p.emoji }} {{ p.name }} — {{ p.tagline }}
      </option>
    </select>
  </label>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { SCENE_OPTIONS } from "../../constants/scenes";
import type { HrPersonalityMeta } from "../../runtime/battle_runtime_adapter";
import { runtimeAdapter } from "../../runtime";

export type StartSessionParams = {
  userName: string;
  sceneId: string;
  roleId: string;
  hrPersonalityId: string;
};

const FALLBACK_PERSONALITIES: HrPersonalityMeta[] = [
  { personality_id: "hr_newbie", name: "菜鸟新人", tagline: "紧张没底气，容易说漏信息", emoji: "🐣" },
  { personality_id: "hr_robot", name: "冷漠流程型", tagline: "按系统流程办事，几乎无情绪波动", emoji: "🤖" },
  { personality_id: "hr_aggressive", name: "强势压价型", tagline: "开门见山压价，耐心极低", emoji: "💪" },
  { personality_id: "hr_honest", name: "老实人型", tagline: "真诚坦率，容易被说服", emoji: "😇" },
  { personality_id: "hr_smiling_tiger", name: "笑面虎型", tagline: "表面热情，话术圆滑", emoji: "😊" },
];

const userName = ref("");
const roleId = ref("role_backend");
const sceneId = ref("scene_001");
const hrPersonalityId = ref("hr_smiling_tiger");
const personalities = ref<HrPersonalityMeta[]>(FALLBACK_PERSONALITIES);

const selectedPersonality = computed(() =>
  personalities.value.find((p) => p.personality_id === hrPersonalityId.value)
);

const emit = defineEmits<{
  displayChange: [payload: { name: string; tagline: string }];
}>();

function emitDisplay() {
  emit("displayChange", {
    name: selectedPersonality.value?.name || "HR",
    tagline: selectedPersonality.value?.tagline || "HR负责人 · A轮AI初创公司",
  });
}

watch([hrPersonalityId, personalities], emitDisplay, { immediate: true, deep: true });

onMounted(async () => {
  if (!runtimeAdapter.listHrPersonalities) return;
  try {
    const list = await runtimeAdapter.listHrPersonalities();
    if (list.length) personalities.value = list;
  } catch {
    // keep fallback
  }
});

function reset() {
  roleId.value = "role_backend";
  sceneId.value = "scene_001";
  hrPersonalityId.value = "hr_smiling_tiger";
  userName.value = "";
}

function getSessionParams(): StartSessionParams {
  return {
    userName: userName.value.trim(),
    sceneId: sceneId.value,
    roleId: roleId.value,
    hrPersonalityId: hrPersonalityId.value,
  };
}

defineExpose({
  reset,
  getSessionParams,
});
</script>
