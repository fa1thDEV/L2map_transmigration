# Cross-Chronicle Map Comparison: 22_22.unr vs 22_22.unr

## 1. Core Engine & File Metrics
| Metric | Map A (Baseline) | Map B (Target) | Evolution / Delta |
| :--- | :--- | :--- | :--- |
| **File Name** | `22_22.unr` | `22_22.unr` | - |
| **File Size** | 7.57 MB | 25.48 MB | +17.91 MB |
| **Unreal Engine Version** | Version 123 (Lic 37) | Version 133 (Lic 40) | Version Bump |
| **Total Placed Actors** | 8,129 | 14,808 | +6,679 actors |
| **Imported Packages** | 54 | 93 | +39 packages |
| **Unique 3D Meshes** | 311 | 599 | +288 meshes |

## 2. Actor Class Count Breakdown
| Actor Class | Map A Count | Map B Count | Change |
| :--- | :---: | :---: | :--- |
| `AmbientSoundObject` | 2,353 | 2,410 | **+57** |
| `AmbientSoundWObject` | 0 | 221 | **+221** |
| `AmbientVolume` | 0 | 10 | **+10** |
| `AmbientVolumeSound` | 0 | 15 | **+15** |
| `BeamEmitter` | 0 | 14 | **+14** |
| `BlockingVolume` | 22 | 143 | **+121** |
| `Brush` | 291 | 341 | **+50** |
| `Camera` | 15 | 18 | **+3** |
| `CameraVolume` | 0 | 3 | **+3** |
| `DynamicProjector` | 0 | 1 | **+1** |
| `Emitter` | 150 | 494 | **+344** |
| `FluidSurfaceInfo` | 0 | 1 | **+1** |
| `L2FogInfo` | 1 | 4 | **+3** |
| `L2MovableStaticMeshActor` | 0 | 115 | **+115** |
| `Level` | 1 | 1 | **=** |
| `LevelInfo` | 1 | 1 | **=** |
| `LevelSummary` | 1 | 1 | **=** |
| `Light` | 94 | 338 | **+244** |
| `MarkProjector` | 0 | 2 | **+2** |
| `MeshEmitter` | 9 | 196 | **+187** |
| `Model` | 338 | 529 | **+191** |
| `Mover` | 10 | 10 | **=** |
| `MusicVolume` | 16 | 19 | **+3** |
| `NMoon` | 1 | 1 | **=** |
| `NMovableSunLight` | 1 | 1 | **=** |
| `NSun` | 1 | 1 | **=** |
| `PhysicsVolume` | 1 | 1 | **=** |
| `PlayerStart` | 10 | 36 | **+26** |
| `Polys` | 338 | 529 | **+191** |
| `Projector` | 0 | 1 | **+1** |
| `ReachSpec` | 0 | 4 | **+4** |
| `ServerBlockingVolume` | 0 | 1 | **+1** |
| `ShadowProjector` | 0 | 2 | **+2** |
| `SkyZoneInfo` | 1 | 1 | **=** |
| `Spotlight` | 0 | 54 | **+54** |
| `SpriteEmitter` | 617 | 1,515 | **+898** |
| `StaticMeshActor` | 2,030 | 3,527 | **+1497** |
| `StaticMeshInstance` | 1,541 | 3,948 | **+2407** |
| `TerrainInfo` | 1 | 1 | **=** |
| `TerrainSector` | 256 | 256 | **=** |
| `TrailEmitter` | 4 | 0 | **-4** |
| `VertMeshEmitter` | 0 | 13 | **+13** |
| `WaterVolume` | 8 | 11 | **+3** |
| `ZoneInfo` | 17 | 18 | **+1** |

## 3. New Engine Classes Added in Map B (15)
These classes were introduced in the newer chronicle and will cause crashes if imported into an engine that lacks them:
- `+AmbientSoundWObject`
- `+AmbientVolume`
- `+AmbientVolumeSound`
- `+BeamEmitter`
- `+CameraVolume`
- `+DynamicProjector`
- `+FluidSurfaceInfo`
- `+L2MovableStaticMeshActor`
- `+MarkProjector`
- `+Projector`
- `+ReachSpec`
- `+ServerBlockingVolume`
- `+ShadowProjector`
- `+Spotlight`
- `+VertMeshEmitter`

## 4. Package Additions in Map B (43)
- `+AmbSound4`
- `+AmbSound5`
- `+Annihilation_Dungeon_T2`
- `+BG_Effect_S`
- `+Dethrone_Water_F_T`
- `+Dion_Partisan_S`
- `+Fafurion_Boss_S`
- `+Fafurion_Field_S`
- `+Gludio_Refine_S`
- `+Gludio_Rewindmill_S`
- `+Gludio_refine_T`
- `+Godard_SPA_Azit_S`
- `+Godard_Village_S`
- `+LineageBgMeshes_T`
- `+LineageEffectMeshes`
- `+LineageEffectsStaticmeshes2`
- `+LineageEffectsTextures3`
- `+LineageEffectsTextures4`
- `+Magmell_arcan_T`
- `+MonSound_Branch`
- `+New_Speaking_Dark_V_S`
- `+New_Speaking_V_S`
- `+New_Speaking_V_T`
- `+Oren_HEV_S`
- `+Oren_HEV_T`
- `+Oren_RefineField_S`
- `+Rune_Village_S`
- `+Rune_swamp_S`
- `+Rune_village_03_T`
- `+SkillSound`
- `+SkillSound12`
- `+SkillSound14`
- `+SkillSound_Branch`
- `+StepSound`
- `+Superion_Du_S`
- `+Superion_S`
- `+Superion_T`
- `+T_oren`
- `+ThemePark_Wedding_S`
- `+bereth_S`
- `+field_deco_T`
- `+innadrile_eva_waterGarden_S`
- `+themepark_wedding_t`

## 5. Top 15 Most Placed 3D Models in Map B
| Static Mesh Reference | Placement Count | Present in Map A? |
| :--- | :---: | :---: |
| `field_deco_S.diongiranstone.dgstone11` | 203 | Yes |
| `Giran_Village_S.Spring.Giran_Sflower_02d` | 122 | **NEW** |
| `Superion_S.superion_tree_02` | 104 | **NEW** |
| `field_deco_S.diongiranstone.dgstone10` | 89 | Yes |
| `FX_E_S.Flameset.Default_Flame01` | 78 | Yes |
| `field_deco_S.diongiranstone.dgstone04` | 74 | Yes |
| `V_Obj_S.Speaking_Town_S.O_Box02` | 67 | Yes |
| `Agit_B_s.7_0` | 60 | Yes |
| `Dion_tree_S.red_mt.DionRtree2` | 53 | Yes |
| `speaking1F_S.Cylinder01` | 52 | Yes |
| `Superion_S.superion_block_03` | 48 | **NEW** |
| `Giran_Village_S.Spring.Giran_Sflower_01d` | 46 | **NEW** |
| `field_deco_S.diongiranstone.dgstone07` | 46 | Yes |
| `Agit_B_s.10_0` | 45 | Yes |
| `V_Obj_S.Light_A.Giran_StLight02` | 45 | Yes |
