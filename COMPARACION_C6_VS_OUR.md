# Cross-Chronicle Map Comparison: 22_22.unr vs 22_22.unr

## 1. Core Engine & File Metrics
| Metric | Map A (Baseline) | Map B (Target) | Evolution / Delta |
| :--- | :--- | :--- | :--- |
| **File Name** | `22_22.unr` | `22_22.unr` | - |
| **File Size** | 6.88 MB | 7.57 MB | +0.69 MB |
| **Unreal Engine Version** | Version 123 (Lic 28) | Version 123 (Lic 37) | Same |
| **Total Placed Actors** | 7,074 | 8,129 | +1,055 actors |
| **Imported Packages** | 42 | 54 | +12 packages |
| **Unique 3D Meshes** | 287 | 311 | +24 meshes |

## 2. Actor Class Count Breakdown
| Actor Class | Map A Count | Map B Count | Change |
| :--- | :---: | :---: | :--- |
| `AmbientSoundObject` | 2,301 | 2,353 | **+52** |
| `BlockingVolume` | 13 | 22 | **+9** |
| `Brush` | 291 | 291 | **=** |
| `Camera` | 12 | 15 | **+3** |
| `Emitter` | 0 | 150 | **+150** |
| `L2FogInfo` | 0 | 1 | **+1** |
| `Level` | 1 | 1 | **=** |
| `LevelInfo` | 1 | 1 | **=** |
| `LevelSummary` | 1 | 1 | **=** |
| `Light` | 91 | 94 | **+3** |
| `MeshEmitter` | 0 | 9 | **+9** |
| `Model` | 329 | 338 | **+9** |
| `Mover` | 10 | 10 | **=** |
| `MusicVolume` | 16 | 16 | **=** |
| `NMoon` | 1 | 1 | **=** |
| `NMovableSunLight` | 1 | 1 | **=** |
| `NSun` | 1 | 1 | **=** |
| `PhysicsVolume` | 1 | 1 | **=** |
| `PlayerStart` | 6 | 10 | **+4** |
| `Polys` | 329 | 338 | **+9** |
| `SkyZoneInfo` | 1 | 1 | **=** |
| `SpriteEmitter` | 0 | 617 | **+617** |
| `StaticMeshActor` | 1,936 | 2,030 | **+94** |
| `StaticMeshInstance` | 1,450 | 1,541 | **+91** |
| `TerrainInfo` | 1 | 1 | **=** |
| `TerrainSector` | 256 | 256 | **=** |
| `TrailEmitter` | 0 | 4 | **+4** |
| `WaterVolume` | 8 | 8 | **=** |
| `ZoneInfo` | 17 | 17 | **=** |

## 3. New Engine Classes Added in Map B (5)
These classes were introduced in the newer chronicle and will cause crashes if imported into an engine that lacks them:
- `+Emitter`
- `+L2FogInfo`
- `+MeshEmitter`
- `+SpriteEmitter`
- `+TrailEmitter`

## 4. Package Additions in Map B (12)
- `+AmbSound2`
- `+AmbSound3`
- `+BG_Effect_T`
- `+Field_Deco_Artifact2_T`
- `+GL_CV_S`
- `+Glacia_undying_T`
- `+Gludio_Port_S`
- `+LineageEffectsStaticmeshes`
- `+LineageEffectsTextures`
- `+LineageEffectsTextures2`
- `+Spirit_island_V_S`
- `+V_Obj_Orc_S`

## 5. Top 15 Most Placed 3D Models in Map B
| Static Mesh Reference | Placement Count | Present in Map A? |
| :--- | :---: | :---: |
| `field_deco_S.diongiranstone.dgstone11` | 207 | Yes |
| `field_deco_S.diongiranstone.dgstone10` | 96 | Yes |
| `field_deco_S.diongiranstone.dgstone04` | 79 | Yes |
| `V_Obj_S.Speaking_Town_S.O_Box02` | 73 | Yes |
| `Agit_B_s.7_0` | 60 | Yes |
| `V_Obj_S.Light_A.Giran_StLight02` | 56 | Yes |
| `Dion_tree_S.red_mt.DionRtree2` | 54 | Yes |
| `field_deco_S.diongiranstone.dgstone07` | 50 | Yes |
| `field_deco_S.diongiranstone.dgstone08` | 47 | Yes |
| `field_deco_S.diongiranstone.dgstone03` | 47 | Yes |
| `Agit_B_s.10_0` | 45 | Yes |
| `Dion_tree_S.Girantree.girantree2` | 42 | Yes |
| `field_deco_S.diongiranstone.dgstone05` | 39 | Yes |
| `field_deco_S.diongiranstone.dgstone09` | 33 | Yes |
| `Dion_tree_S.guillotineTree.guillotinetree3` | 33 | Yes |
