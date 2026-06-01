<template>
  <div v-if="open" class="settings-backdrop" @click.self="$emit('close')">
    <section class="settings-modal" role="dialog" aria-modal="true" aria-label="设置">
      <header class="settings-header">
        <div>
          <p class="settings-kicker">Settings</p>
          <h2 class="settings-title">开始前设置</h2>
        </div>
        <button type="button" class="settings-close" @click="$emit('close')">×</button>
      </header>

      <div class="settings-body">
        <label class="field">
          <span class="field-label">音量</span>
          <div class="volume-row">
            <input v-model.number="draft.volume" type="range" min="0" max="1" step="0.01" />
            <span class="volume-value">{{ Math.round(draft.volume * 100) }}%</span>
          </div>
        </label>

        <label class="field">
          <span class="field-label">语音识别灵敏度</span>
          <div class="volume-row">
            <input v-model.number="draft.asrSensitivity" type="range" min="0" max="1" step="0.01" />
            <span class="volume-value">{{ Math.round(draft.asrSensitivity * 100) }}%</span>
          </div>
          <p class="field-hint">环境越嘈杂可适当调低；太低可能漏字，太高可能把噪音也当成说话。</p>
        </label>

        <label class="field">
          <span class="field-label">你的百炼 API Key</span>
          <input
            v-model="draft.userApiKey"
            type="password"
            autocomplete="off"
            placeholder="sk-..."
          />
          <p class="field-hint">
            需填写阿里云百炼平台的 API Key。未配置时，公开模式下无法使用在线服务。
          </p>
        </label>

        <div class="debug-box">
          <div class="debug-head">
            <div>
              <div class="field-label">开发者模式</div>
              <p class="field-hint">
                输入密码后，可使用当前项目自带的 API Key。若你已填写自己的 API Key，则始终优先使用你自己的 Key。
              </p>
            </div>
            <label class="switch">
              <input v-model="draft.internalDebugEnabled" type="checkbox" />
              <span>{{ draft.internalDebugEnabled ? "已开启" : "未开启" }}</span>
            </label>
          </div>

          <label class="field">
            <span class="field-label">开发者密码</span>
            <input
              v-model="draft.debugPassword"
              type="password"
              autocomplete="off"
              placeholder="输入开发者模式密码"
              :disabled="!draft.internalDebugEnabled"
            />
            <p class="field-hint">
              密码由服务端环境变量 `DEV_UNLOCK_PASSWORD` 控制；未配置时默认值为 `20260531`。
            </p>
          </label>
        </div>

        <p class="settings-note">
          提示：设置仅保存在当前浏览器本地，不会写入排行榜或数据库。
        </p>
      </div>

      <footer class="settings-footer">
        <button type="button" class="btn-ghost" @click="resetDraft">恢复默认</button>
        <button type="button" class="btn-primary" @click="submit">保存设置</button>
      </footer>
    </section>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from "vue";
import type { AppSettings } from "../../utils/app_settings";

const props = defineProps<{
  open: boolean;
  settings: AppSettings;
}>();

const emit = defineEmits<{
  close: [];
  save: [value: AppSettings];
}>();

const draft = reactive<AppSettings>({ ...props.settings });

watch(
  () => props.settings,
  (value) => {
    Object.assign(draft, value);
  },
  { deep: true, immediate: true },
);

watch(
  () => props.open,
  (value) => {
    if (value) {
      Object.assign(draft, props.settings);
    }
  },
);

function resetDraft() {
  draft.volume = 0.6;
  draft.asrSensitivity = 0.5;
  draft.userApiKey = "";
  draft.internalDebugEnabled = false;
  draft.debugPassword = "";
}

function submit() {
  emit("save", {
    volume: Math.max(0, Math.min(1, Number(draft.volume) || 0)),
    userApiKey: draft.userApiKey,
    internalDebugEnabled: draft.internalDebugEnabled,
    debugPassword: draft.debugPassword,
    asrSensitivity: Math.max(0, Math.min(1, Number(draft.asrSensitivity) || 0)),
  });
}
</script>

<style scoped>
.settings-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(10, 22, 40, 0.46);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 50;
}

.settings-modal {
  width: min(100%, 360px);
  max-height: min(85vh, 620px);
  overflow: auto;
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 20px 60px rgba(9, 24, 41, 0.24);
}

.settings-header,
.settings-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px;
}

.settings-header {
  border-bottom: 1px solid #edf1f4;
}

.settings-kicker {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #00a88d;
  font-weight: 700;
}

.settings-title {
  margin: 4px 0 0;
  font-size: 18px;
  color: #152033;
}

.settings-close {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: #f2f5f8;
  color: #516274;
  font-size: 22px;
  cursor: pointer;
}

.settings-body {
  display: grid;
  gap: 14px;
  padding: 16px 18px 6px;
}

.field {
  display: grid;
  gap: 8px;
}

.field-label {
  font-size: 13px;
  font-weight: 700;
  color: #1a1a2e;
}

.field input[type="password"],
.field input[type="text"] {
  height: 40px;
  border-radius: 12px;
  border: 1px solid #d7dfe7;
  padding: 0 12px;
  font-size: 13px;
  color: #1a1a2e;
}

.field input:focus {
  outline: none;
  border-color: #00bfa6;
  box-shadow: 0 0 0 3px rgba(0, 191, 166, 0.12);
}

.field input:disabled {
  background: #f5f7fa;
  color: #9aa8b7;
}

.field-hint,
.settings-note {
  margin: 0;
  font-size: 11px;
  line-height: 1.5;
  color: #728194;
}

.debug-box {
  display: grid;
  gap: 12px;
  padding: 14px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(10, 22, 40, 0.04), rgba(0, 194, 162, 0.08));
  border: 1px solid rgba(0, 194, 162, 0.18);
}

.debug-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #1a1a2e;
  white-space: nowrap;
}

.volume-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.volume-row input[type="range"] {
  flex: 1;
}

.volume-value {
  width: 44px;
  text-align: right;
  font-size: 12px;
  font-weight: 700;
  color: #007a68;
}

.settings-footer {
  border-top: 1px solid #edf1f4;
}

.btn-ghost,
.btn-primary {
  height: 40px;
  border: none;
  border-radius: 12px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.btn-ghost {
  background: #f2f5f8;
  color: #56667a;
}

.btn-primary {
  background: linear-gradient(135deg, #00c2a2, #00a88d);
  color: #fff;
  box-shadow: 0 6px 16px rgba(0, 194, 162, 0.25);
}
</style>
