# Texte → 3D exportable vers Blender, topologie quads (2026-10-25/26)

But : à partir d'un texte, obtenir un modèle 3D texturé (PBR) avec une topologie propre en quads, importable dans Blender, sur la 3060 Laptop 6 Go.

## Pipeline retenue
```
texte ──Klein 4B──> image de référence ──TRELLIS.2 (512)──> maillage dense texturé (GLB, 200k tris)
      ──Blender : voxel remesh 1/160 → QuadriFlow → UV → bake PBR──> GLB + .blend en quads (8-12k)
```
Commandes :
```
python3 gen.py <nom> "<description de l'objet>" --models trellis   # ComfyUI doit tourner (--lowvram --disable-pinned-memory)
./quad.sh out/<nom>/trellis_r512_s42.glb 10000                       # quads + bake, Blender 5.2 Windows
./sheet.sh <fichier.glb>                                             # planche 4 vues texturées + 4 vues filaires
```
Sorties : `out/<nom>/ref.png`, `<modèle>_r512_s42.glb` (dense), `..._quad<N>.glb` + `.blend` (textures intégrées), planches dans `sheets/`, temps dans `gen.log`.

## Modèles (téléchargés le 2026-10-25, 15,2 Go)
Tout passe par les nœuds **natifs** de ComfyUI 0.42 (`comfy_extras/nodes_trellis2.py`, `nodes_mesh_postprocess.py`), donc pas de compilation CUDA ni de nouvel environnement. Le graphe reprend le template `3d_pixal3d_trellis2_image_to_model`.

| Fichier | Taille | Rôle |
|---|---|---|
| `trellis_2_int8_convrot.safetensors` (TRELLIS.2 4B, MIT) | 5,25 Go | image → structure → forme → texture PBR |
| `pixal3d_int8_convrot.safetensors` (Pixal3D, MIT) | 5,58 Go | variante « pixel-aligned » de TRELLIS.2 |
| `trellis_2_shape_vae_bf16` + `trellis_2_texture_vae_bf16` | 2,05 Go | VAE partagés |
| `dino_v3_L_naf_fp32` | 1,22 Go | encodeur d'image |
| `birefnet` + `moge_2_vitl_normal_fp16` | 1,10 Go | détourage ; FOV caméra pour Pixal3D |

Écartés sans téléchargement : Hunyuan3D 2.1, parce que 7,4 Go font dépasser le budget de 20 Go et que le nœud natif ne fournit que la forme, sans texture ; Hunyuan3D 2.0 pour la même raison.

## Mise au point sur 6 Go (ce qui a cassé, et pourquoi)
1. **Cascade 1024 impossible sur 6 Go.**
   - L'échantillonnage à 1024 passe avec deux réglages : décharger tout avant (`VRAM_Debug` de KJNodes) et monter `ModelMemoryUsageFactorOverride` à 12 (6 par défaut). Il est très lent : 12 steps en 12 min (60 s/step).
   - Le décodage VAE de la forme à 1024 fait ensuite OOM. Le MLP des `SparseConvNeXtBlock3d` alloue 3 Go d'un bloc : corrigé par un patch qui le découpe (`comfyui/custom_nodes/trellis2_lowvram/`, sortie identique).
   - Mais `SparseResBlockC2S3d.conv1` refait OOM juste après (un tenseur N × 8C de 3 Go). Ça ne se découpe pas simplement.
   - → **Pipeline 512 pur**, prévu par TRELLIS.2 : forme décodée directement depuis l'étage 512, sans upsample. Il gagne aussi les 12 min de l'étage 1024. C'est le défaut de `gen.py` (`--res 512`). Le patch du MLP reste installé, il ne gêne pas.
2. **`RemeshMesh` en grille 768 fait OOM** sur une forme 512 → grille = `min(res, 768)` = 512.
3. Avec `--cache-none` absent, ComfyUI garde les étages en cache : relancer un graphe dont seule la fin change repart du nœud modifié.

## Temps et mémoire (TRELLIS.2 / Pixal3D, 512, seed 42, sans cache)
| Objet | TRELLIS.2 | Pixal3D | VRAM max |
|---|---|---|---|
| Lanterne | 306 s | 349 s | 4,5 / 5,3 Go |
| Renard | 383 s | 346 s | 4,6 / 4,5 Go |
| Fauteuil | 416 s | 452 s | 4,8 / 4,6 Go |
| Coffre | (232 s, en partie en cache) | 493 s | 4,6 / 4,2 Go |

Image de référence Klein 1024² : 140 à 165 s (225 s pour la première, chargement inclus). Quads + bake : 21 à 31 s par objet. **Total texte → quads : environ 9 à 11 min.**

## Comparaison TRELLIS.2 / Pixal3D (mêmes images de référence)
| Objet | TRELLIS.2 | Pixal3D |
|---|---|---|
| Coffre | Excellent, droit. Rivets, cadenas et charnières présents | Texture un peu plus fidèle (planches), mais **objet incliné** |
| Lanterne | Forme excellente (anse, cage). **Laiton rendu cuivré** | **Vrai laiton**, droit. Anse un peu tordue |
| Renard | Bon, mais **écharpe verte rendue kaki** | **Couleurs fidèles** (écharpe verte), droit |
| Fauteuil | Bon. Tissu rendu comme du cuir, une tache bleue sur le bois | Couleurs fidèles, mais **incliné** |

- Pixal3D reconstruit dans le repère de la caméra. Il est droit quand l'image est prise à hauteur d'objet (lanterne, renard) et penché quand elle est vue d'en haut (coffre, fauteuil). TRELLIS.2 sort toujours dans un repère canonique, posé à plat.
- Le verre devient opaque avec les deux modèles : aucune transparence n'est générée.
- **Test `--view eye`** (référence demandée « à hauteur d'objet », coffre et fauteuil, Pixal3D : 412 et 366 s) : **ne redresse pas de façon fiable.** Klein garde une légère plongée sur le coffre, qui reste penché, et le fauteuil est presque droit, mais pas tout à fait. La géométrie Pixal3D est en revanche la plus détaillée du test (rivets, planches, capitonnage).

### Verdict
- **Retenu par défaut : TRELLIS.2.** Toujours droit et posé dans un repère canonique, donc automatisable sans retouche. Forme au moins aussi bonne. Ses couleurs dérivent parfois (laiton → cuivre, vert → kaki).
- **Pixal3D, en option** (`--models pixal`) : textures plus fidèles à l'image sur 4 objets sur 4, mais l'orientation dépend de la caméra de la référence et demande une rotation manuelle dans Blender. Même coût en temps. Les 5,6 Go sont gardés pour ce cas.
- Piste non testée : redresser Pixal3D automatiquement (rotation inverse du tangage de la caméra, ou alignement sur la sortie TRELLIS.2).

## Quads dans Blender (`quad.py`)
Chaque étape est là parce que la version sans elle a échoué :
- **QuadriFlow refusait les maillages TRELLIS.2.** À l'import GLB, les coutures UV ouvrent le maillage (64 k bords libres). Même soudé, il reste non manifold (341 bords, 212 arêtes à 3 faces). → **Remesh voxel systématique** à 1/160 de la taille : une seule surface fermée.
- **QuadriFlow refusait aussi la sortie voxel**, pourtant parfaitement manifold. Son contrôle préalable rejette les arêtes de moins de **1e-4 en absolu**, et un objet de taille 1 en contient (35 sur le coffre). → QuadriFlow tourne sur une copie agrandie ×100, puis on remet à l'échelle.
- **QuadriFlow boucle sans fin** (plus de 20 min) sur le renard et la lanterne avec `use_preserve_sharp`, ou avec un voxel 1/256. → Sans `preserve_sharp` et en voxel 1/160 : 10 s. Le coffre était passé dans tous les cas.
- **Bake** : la passe Diffuse Color de Cycles multiplie la couleur par (1 − métal)(1 − transmission), ce qui donnait du fer noir et un verre noir. → La couleur de base, la rugosité et le métal sont bakés via l'émission (valeur brute), la normale via NORMAL. Cible 2048², bake GPU (`CPU` en 4e argument si ComfyUI tourne).
- **Mémoire Windows** : WSL réserve 14 Go sur 15,6. Pendant une génération ComfyUI, Blender (côté Windows) est relégué en swap. Lancer `quad.sh` quand ComfyUI est au repos, ou après `POST /free`.

Résultats (100 % de quads) : coffre 7 696 faces, renard 10 824, lanterne 11 945, fauteuil 9 268. Grille régulière, textures conservées. À 8-12 k quads, les petites pièces (cadenas, charnières, fils de la cage) deviennent des « blobs » géométriques. Leur détail reste dans la normal map bakée, que les planches Workbench n'affichent pas. Monter la cible (`quad.sh <glb> 20000`) pour garder plus de géométrie.

## Écarté en cours de route
- Instant Meshes (meilleur que QuadriFlow sur les formes organiques) : le téléchargement d'un exécutable externe a été bloqué par les règles de sécurité de la session. QuadriFlow, déjà intégré à Blender, suffit une fois réglé comme ci-dessus.
