import { computed, type Ref } from "vue";
import type { SessionState } from "../runtime/battle_runtime_adapter";

export type HrMood = "calm" | "angry" | "aggrieved";
export type PlayerMood = "panicked" | "confident" | "pleading";

export type MoodMeta = {
  emoji: string;
  label: string;
  hint: string;
};

export const HR_MOOD_META: Record<HrMood, MoodMeta> = {
  calm: { emoji: "😌", label: "沉稳", hint: "HR 气定神闲，节奏尽在掌握" },
  angry: { emoji: "😠", label: "愤怒", hint: "HR 耐心告急，谈判濒临破裂" },
  aggrieved: { emoji: "🥺", label: "委屈", hint: "HR 觉得被步步紧逼，有点吃不消" },
};

export const PLAYER_MOOD_META: Record<PlayerMood, MoodMeta> = {
  panicked: { emoji: "😰", label: "慌张", hint: "底牌暴露过多，得赶紧找补" },
  confident: { emoji: "😎", label: "自信", hint: "局势尚可，可以继续周旋" },
  pleading: { emoji: "🙏", label: "求饶", hint: "HR 满意度太低，先缓和气氛" },
};

export function resolveHrMood(session: SessionState | null): HrMood {
  if (!session) return "calm";
  const patience = session.hr_patience ?? 70;
  const exposure = session.info_exposure ?? 0;
  const traps = session.trap_count ?? 0;

  if (patience <= 30) return "angry";
  if (traps >= 2 || (patience <= 52 && exposure >= 50)) return "aggrieved";
  return "calm";
}

export function resolvePlayerMood(session: SessionState | null): PlayerMood {
  if (!session) return "confident";
  const patience = session.hr_patience ?? 70;
  const exposure = session.info_exposure ?? 0;

  if (exposure >= 65) return "panicked";
  if (patience <= 35) return "pleading";
  return "confident";
}

export function useBattleMood(session: Ref<SessionState | null>) {
  const hrMood = computed(() => resolveHrMood(session.value));
  const playerMood = computed(() => resolvePlayerMood(session.value));
  const hrMoodMeta = computed(() => HR_MOOD_META[hrMood.value]);
  const playerMoodMeta = computed(() => PLAYER_MOOD_META[playerMood.value]);

  return { hrMood, playerMood, hrMoodMeta, playerMoodMeta };
}
