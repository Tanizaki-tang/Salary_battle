<template>
  <StartPageShell
    name="HR"
    company="灵创科技"
    tagline="本次面试官随机分配 · 灵创科技"
    :loading="loading"
    :error="error"
    @accept="onAccept"
    @accept-voice="onAcceptVoice"
    @reset="onReset"
  >
    <ProdStartForm ref="formRef" />
  </StartPageShell>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import ProdStartForm from "../components/start/ProdStartForm.vue";
import StartPageShell from "../components/start/StartPageShell.vue";
import { runtimeAdapter } from "../runtime";
import { resolveApiBaseUrl } from "../utils/api_base_url";

const router = useRouter();
const loading = ref(false);
const error = ref("");
const formRef = ref<InstanceType<typeof ProdStartForm> | null>(null);
const baseURL = resolveApiBaseUrl();

function onReset() {
  formRef.value?.reset();
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
    headers: { "Content-Type": "application/json" },
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
  if (validationError) {
    error.value = validationError;
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
  if (validationError) {
    error.value = validationError;
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
