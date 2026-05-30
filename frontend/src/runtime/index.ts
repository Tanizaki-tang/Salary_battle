import { apiRuntimeAdapter } from "./api_runtime_adapter";
import type { BattleRuntimeAdapter } from "./battle_runtime_adapter";
import { mockRuntimeAdapter } from "./mock_runtime_adapter";

const mode = (import.meta.env.VITE_RUNTIME_MODE || "api").toLowerCase();

export const runtimeAdapter: BattleRuntimeAdapter = mode === "mock" ? mockRuntimeAdapter : apiRuntimeAdapter;

export const runtimeMode = mode;
