export type SceneOption = {
  sceneId: string;
  roleId: string;
  label: string;
};

export const SCENE_OPTIONS: SceneOption[] = [
  { sceneId: "scene_001", roleId: "role_backend", label: "初创公司后端岗" },
  { sceneId: "scene_002", roleId: "role_product", label: "中型互联网产品岗" },
  { sceneId: "scene_003", roleId: "role_sales", label: "消费行业销售岗" },
];

export function findSceneOption(sceneId: string): SceneOption | undefined {
  return SCENE_OPTIONS.find((s) => s.sceneId === sceneId);
}
