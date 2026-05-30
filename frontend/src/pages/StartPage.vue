<template>
  <section class="page-root">
    <div class="phone-shell">
      <div class="phone-notch"></div>
      <div class="status-bar dark">
        <span>9:41</span>
        <span>📶 🔋</span>
      </div>
      <div class="incoming-bg">
        <div class="incoming-label">Boss直聘 · 面试电话</div>

        <div class="incoming-avatar">👩‍💼</div>
        <div class="incoming-name">张敏</div>
        <div class="incoming-company">灵创科技</div>
        <div class="incoming-role">HR负责人 · A轮AI初创公司</div>

        <div class="selectors">
          <label>
            昵称：
            <input v-model="userName" maxlength="24" placeholder="请输入你的名字（如：小陈）" />
          </label>
          <label>
            角色：
            <select v-model="roleId">
              <option value="role_backend">后端开发</option>
              <option value="role_product">产品经理</option>
              <option value="role_sales">销售</option>
            </select>
          </label>
          <label>
            场景：
            <select v-model="sceneId">
              <option value="scene_001">scene_001 初创后端岗</option>
              <option value="scene_002">scene_002 互联网产品岗</option>
              <option value="scene_003">scene_003 消费销售岗</option>
            </select>
          </label>
        </div>

        <div class="incoming-reminder">🔔 点击接听进入谈判（{{ mode }}）</div>
        <p v-if="error" class="error">{{ error }}</p>

        <div class="incoming-actions">
          <div class="incoming-btn">
            <button class="incoming-btn-circle incoming-btn-decline" @click="resetSelections">✕</button>
            <span class="incoming-btn-label">重置</span>
          </div>
          <div class="incoming-btn">
            <button class="incoming-btn-circle incoming-btn-accept" @click="startGame" :disabled="loading">
              {{ loading ? "…" : "✓" }}
            </button>
            <span class="incoming-btn-label">{{ loading ? "创建中" : "接听" }}</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { runtimeAdapter, runtimeMode } from "../runtime";

const router = useRouter();
const loading = ref(false);
const error = ref("");
const roleId = ref("role_backend");
const sceneId = ref("scene_001");
const userName = ref("");
const mode = runtimeMode;

function resetSelections() {
  roleId.value = "role_backend";
  sceneId.value = "scene_001";
  userName.value = "";
  error.value = "";
}

async function startGame() {
  loading.value = true;
  error.value = "";
  try {
    const userId = `user_${Date.now()}`;
    const normalizedName = userName.value.trim();
    const data = await runtimeAdapter.createSession(userId, sceneId.value, roleId.value, normalizedName);
    sessionStorage.setItem("currentSession", JSON.stringify(data.session));
    sessionStorage.setItem("hrOpening", data.hr_opening);
    router.push(`/battle/${data.session.session_id}`);
  } catch (e) {
    error.value = `创建对局失败：${String(e)}`;
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.page-root { width: 375px; height: 700px; }
.phone-shell { width: 100%; height: 100%; border-radius: 32px; overflow: hidden; position: relative; display: flex; flex-direction: column; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), 0 0 0 2px #1a1a1a; background: #fff; }
.phone-notch { position: absolute; top: 8px; left: 50%; transform: translateX(-50%); width: 100px; height: 24px; background: #1a1a1a; border-radius: 0 0 16px 16px; z-index: 10; }
.status-bar { height: 36px; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; font-size: 11px; font-weight: 600; color: #fff; flex-shrink: 0; }
.status-bar.dark { background: #1a1a2e; }
.incoming-bg {
  background: linear-gradient(180deg, #0d0d1a 0%, #1a1a2e 60%, #16213e 100%);
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 34px 24px;
  color: #fff;
}
.incoming-label {
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-top: 24px;
}
.incoming-avatar {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e8f5e9, #a5d6a7);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 44px;
  margin-top: 28px;
}
.incoming-name { font-size: 24px; font-weight: 700; margin-top: 18px; }
.incoming-company { color: rgba(255,255,255,0.7); font-size: 14px; margin-top: 3px; }
.incoming-role { color: rgba(255,255,255,0.5); font-size: 12px; margin-top: 2px; }
.selectors {
  margin-top: 22px;
  width: 100%;
  display: grid;
  gap: 8px;
}
.selectors label { font-size: 12px; color: rgba(255,255,255,0.85); display: grid; gap: 4px; }
.selectors select {
  height: 34px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.2);
  background: rgba(255,255,255,0.08);
  color: #fff;
  padding: 0 10px;
}
.selectors input {
  height: 34px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.2);
  background: rgba(255,255,255,0.08);
  color: #fff;
  padding: 0 10px;
  outline: none;
}
.selectors input::placeholder { color: rgba(255,255,255,0.55); }
.incoming-reminder { color: rgba(255,255,255,0.45); font-size: 11px; margin-top: 16px; letter-spacing: 1px; }
.incoming-actions {
  margin-top: auto;
  padding-bottom: 20px;
  display: flex;
  justify-content: center;
  gap: 60px;
  width: 100%;
}
.incoming-btn { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.incoming-btn-circle {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: none;
  font-size: 28px;
  color: #fff;
}
.incoming-btn-accept { background: #00c2a2; }
.incoming-btn-decline { background: rgba(255,255,255,0.16); color: #ff6b6b; }
.incoming-btn-label { color: rgba(255,255,255,0.6); font-size: 11px; }
.error { margin-top: 8px; color: #ff9aa2; font-size: 12px; }
</style>
