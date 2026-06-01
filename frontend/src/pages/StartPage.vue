<template>
  <StartPageShell
    name="HR"
    :company="selectedScene.company"
    :tagline="selectedScene.tagline"
    :loading="loading"
    :error="error"
    :settings-status="settingsStatus"
    @accept="onAccept"
    @accept-voice="onAcceptVoice"
    @reset="onReset"
    @open-settings="showSettings = true"
  >
    <ProdStartForm ref="formRef" @scene-change="onSceneChange" />
  </StartPageShell>
  <StartSettingsModal
    :open="showSettings"
    :settings="settings"
    @close="showSettings = false"
    @save="onSaveSettings"
  />
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import ProdStartForm from "../components/start/ProdStartForm.vue";
import StartSettingsModal from "../components/start/StartSettingsModal.vue";
import StartPageShell from "../components/start/StartPageShell.vue";
import { findSceneOption } from "../constants/scenes";
import { runtimeAdapter } from "../runtime";
import {
  buildRuntimeAuthHeaders,
  hasDeveloperModeCredential,
  hasRuntimeCredential,
  loadAppSettings,
  saveAppSettings,
  type AppSettings,
} from "../utils/app_settings";
import { resolveApiBaseUrl } from "../utils/api_base_url";

const router = useRouter();
const loading = ref(false);
const error = ref("");
const formRef = ref<InstanceType<typeof ProdStartForm> | null>(null);
const baseURL = resolveApiBaseUrl();
const selectedSceneId = ref("scene_001");
const selectedScene = computed(() => findSceneOption(selectedSceneId.value) || findSceneOption("scene_001")!);
const settings = ref<AppSettings>(loadAppSettings());
const showSettings = ref(false);
const runtimeMode = String(import.meta.env.VITE_RUNTIME_MODE || "api").toLowerCase();

const settingsStatus = computed(() => {
  if (runtimeMode === "mock") {
    return "当前为本地 mock 模式，设置中的 API Key 不参与调用。";
  }
  if (settings.value.userApiKey.trim()) {
    return "已配置你的百炼 API Key，将优先使用你的 Key 发起请求。";
  }
  if (hasDeveloperModeCredential(settings.value)) {
    return "已开启开发者模式；创建对局时会校验密码，校验通过后使用项目自带 API Key。";
  }
  return "未配置服务凭证。请先点右上角设置，填写百炼 API Key，或解锁内部调试版本。";
});

function onSceneChange(payload: { sceneId: string }) {
  selectedSceneId.value = payload.sceneId;
}

function onReset() {
  formRef.value?.reset();
  error.value = "";
}

function ensureRuntimeCredential() {
  if (runtimeMode === "mock") return null;
  if (hasRuntimeCredential(settings.value)) return null;
  return "请先在设置中填写 API Key，或开启开发者模式并输入正确密码";
}

function onSaveSettings(value: AppSettings) {
  settings.value = saveAppSettings(value);
  showSettings.value = false;
  error.value = "";
}

async function createAndStoreSession() {
  const params = formRef.value?.getSessionParams();
  if (!params) throw new Error("表单未就绪");
  const userId = `user_${Date.now()}`;
  const data = await runtimeAdapter.createSession(
    userId,
    params.sceneId,
    params.roleId,
    params.userName,
  );
  sessionStorage.setItem("currentSession", JSON.stringify(data.session));
  sessionStorage.setItem("hrOpening", data.hr_opening);
  if (data.hr_personality_meta) {
    sessionStorage.setItem("hrPersonalityMeta", JSON.stringify(data.hr_personality_meta));
  }
  return data;
}

async function createAndStoreVoiceSession() {
  const params = formRef.value?.getSessionParams();
  if (!params) throw new Error("表单未就绪");
  const userId = `user_${Date.now()}`;
  const body: Record<string, string> = {
    user_id: userId,
    user_name: params.userName || "",
    scene_id: params.sceneId || "",
    role_id: params.roleId || "",
  };
  const res = await fetch(`${baseURL}/api/v1/voice-battle/sessions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...buildRuntimeAuthHeaders(settings.value),
    },
    body: JSON.stringify(body),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(JSON.stringify(json));
  const data = json.data as {
    session: { session_id: string };
    hr_opening: string;
    hr_personality_meta?: unknown;
  };
  sessionStorage.setItem("currentSession", JSON.stringify(data.session));
  sessionStorage.setItem("hrOpening", data.hr_opening);
  if (data.hr_personality_meta) {
    sessionStorage.setItem("hrPersonalityMeta", JSON.stringify(data.hr_personality_meta));
  }
  return data;
}

async function onAccept() {
  const validationError = formRef.value?.validate();
  const credentialError = ensureRuntimeCredential();
  if (validationError || credentialError) {
    error.value = validationError || credentialError || "";
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    const data = await createAndStoreSession();
    router.push(`/battle/${data.session.session_id}`);
  } catch (e) {
    error.value = `创建对局失败：${String(e)}`;
  } finally {
    loading.value = false;
  }
}

async function onAcceptVoice() {
  const validationError = formRef.value?.validate();
  const credentialError = ensureRuntimeCredential();
  if (validationError || credentialError) {
    error.value = validationError || credentialError || "";
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    const data = await createAndStoreVoiceSession();
    router.push(`/voice-battle/${data.session.session_id}`);
  } catch (e) {
    error.value = `创建对局失败：${String(e)}`;
  } finally {
    loading.value = false;
  }
}
</script>
