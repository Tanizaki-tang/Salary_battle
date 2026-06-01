import { GENERATED_SCENE_OPTIONS } from "../generated/scene_specs";

export type SceneOption = {
  sceneId: string;
  roleId: string;
  label: string;
  company: string;
  tagline: string;
  roleLabel: string;
};

export const SCENE_OPTIONS: SceneOption[] = [...GENERATED_SCENE_OPTIONS];

export function findSceneOption(sceneId: string): SceneOption | undefined {
  return SCENE_OPTIONS.find((s) => s.sceneId === sceneId);
}
