# Notes de tests IA (image / vidéo)

Machine : RTX 3060 Laptop 6 Go, 14 Go RAM (WSL2). ComfyUI 0.42.0 dans `comfyui/`, env conda `comfy` (Python 3.12, torch 2.11+cu128).
Lancement : `conda activate comfy && cd comfyui && python main.py --lowvram --disable-pinned-memory` (`--cache-none` écarté le 2026-10-24, voir `webtoon-layers/NOTES.md`)

## Ménage du 2026-10-22
- Une seule install ComfyUI (`comfyui/`) et un seul env (`comfy`). L'ancienne install `ComfyUI/` + env `comfyui` (test Wan2.2-Animate du 05/10) y a été fusionnée puis supprimée.
- Repris de l'ancienne install : nodes GGUF, KJNodes, VideoHelperSuite, WanAnimatePreprocess, controlnet_aux ; modèles Wan2.2-Animate-14B Q3_K_M/Q4_K_M, umt5-xxl Q5_K_M GGUF, clip_vision_h, wan_2.1_vae, LoRA lightx2v, vitpose-l/yolov10m ; entrées dans `comfyui/input/`, sorties dans `comfyui/output/wan_animate_test_2026-10-05/`.
- Deps des nodes installées dans `comfy` avec torch/numpy figés ; OpenCV unique (`opencv-contrib-python-headless`), mediapipe en `--no-deps`.
- Wan2.2-Animate 14B jamais testé jusqu'à la génération : seul le prétraitement a tourné le 05/10 (squelette de pose raté, jambes à plat). Q3 (8,6 Go) plausible en offload, Q4 (11,5 Go) risqué avec 14 Go de RAM. À tester.
- LivePortrait (dossier + env) supprimé ; ses sorties de test sont dans `_archive/LivePortrait/`. Caches pip et conda vidés.

## Image : Animagine XL 4.0 (SDXL anime, 6,94 Go)
- 832x1216, 25 steps, euler_ancestral, cfg 5, `--lowvram`
- 1re génération (chargement modèle inclus) : 48 s
- Génération suivante : ~21 s/image
- Rendu : lineart net, aplats, proche webtoon. Contre-plongée fréquente si le cadrage n'est pas précisé : ajouter `from front`, `upper body`, `full body`, etc.

### Cohérence de personnage par mots-clés seuls (6 scènes, seeds différentes)
Description fixe : `1girl, short black hair, bob cut, amber eyes, red hair ribbon, white sailor uniform, navy blue collar, small mole under left eye`
- Coupe, yeux, ruban, uniforme : reconnaissables sur les 6 images.
- Dérives : position du ruban, couleur/forme du col, grain de beauté parfois absent, âge apparent.
- Suffisant pour un storyboard ; insuffisant pour une série sans LoRA/IP-Adapter.

## Vidéo : LTX-Video 2B 0.9.8 distilled fp8 (4,46 Go) + T5-XXL fp8 (4,89 Go)
Image-to-video, 512x768, 24 fps, 8 steps, cfg 1.0, euler. Les images sources viennent d'Animagine.
Frames sorties en PNG (`comfyui/output/`), assemblées avec ffmpeg en MP4.

| Test | Frames | Durée clip | Temps total (modèles chargés inclus) |
|---|---|---|---|
| Marche en plan large | 49 | ~2 s | 38 s |
| Marche en plan large | 97 | ~4 s | 57 s |
| Gros plan, mouvement subtil | 49 | ~2 s | 36 s |

- Plan large 2 s : mouvement fluide, décor stable, mais le col marin disparaît et les jambes se brouillent en fin de clip.
- Plan large 4 s : dérive nette du personnage (tenue simplifiée, bras qui disparaît). Limite pratique : ~2 s par plan.
- Gros plan : identité bien tenue, clignement et sourire OK ; glitch passager (bouche/œil) en milieu de clip.
- Le trait perd en netteté vs l'image source, et le rendu s'éloigne un peu du webtoon.

## Vidéo : Wan 2.2 TI2V 5B fp16 (10 Go) + umt5-xxl fp8 (6,74 Go) + VAE wan2.2 (1,41 Go)
Image-to-video, 480x832, 24 fps, 20 steps, cfg 5, uni_pc/simple, shift 8. Licence Apache 2.0.
Même options de lancement que LTX (`--lowvram --disable-pinned-memory --cache-none`), passe sans OOM malgré le modèle de 10 Go.

| Test | Frames | Durée clip | Temps total (chargements inclus) |
|---|---|---|---|
| Marche en plan large | 25 | ~1 s | 144 s |
| Marche en plan large | 49 | ~2 s | 240 s |
| Gros plan, mouvement subtil | 49 | ~2 s | 266 s |

- Identité tenue sur 2 s : col marin, ruban, yeux, trait net conservés (LTX perdait le col et le trait).
- Gros plan : aucun glitch visible (LTX en avait un en milieu de clip).
- Mouvement plus sobre que LTX : à compenser par le prompt si on veut plus d'action.
- Coût : ~4-4,5 min pour 2 s de vidéo, soit ~6x plus lent que LTX 2B (38 s) pour une qualité nettement supérieure.
- Wan 14B (14,3 Go x2) hors de portée de la machine.
- 2026-10-24 : le GGUF Q8_0 (5,4 Go) remplace le fp16. Sampling ×2, job −35 % en session, qualité équivalente. Voir `webtoon-layers/NOTES.md`.

### Incident mémoire (à retenir)
Premier lancement avec `--lowvram` seul : OOM CUDA pendant le chargement de T5, thread de calcul planté, serveur à redémarrer.
Fix : `python main.py --lowvram --disable-pinned-memory --cache-none`. Avec ces options, tout passe sans erreur.
Contrepartie de `--cache-none` : les modèles sont rechargés à chaque job.

## Webtoon par calques (`webtoon-layers/`)
Personnage animé sur fond uni → détourage isnet-anime (rembg) → despill → incrustation sur un décor fixe.
Le chroma key et BiRefNet ont été comparés puis écartés. Détails : `webtoon-layers/NOTES.md`.

## Échelle de styles, cartoon → photo (`style-ladder/`, 2026-10-25)
Même scène, 8 styles × 5 modèles × 2 seeds (74 images). Ajoutés : Z-Image Turbo GGUF Q5_K_M, FLUX.2 Klein 4B GGUF Q8_0 (encodeur Qwen3-4B fp8 partagé), Juggernaut XL v9.
- Z-Image et Klein sont les seuls à suivre le style sur toute l'échelle avec des mains et des visages propres. Klein : 92 s/image, Z-Image : 163 s/image.
- Wan 5B en T2I est écarté pour l'image fixe : le plus lent (161 s), sans être meilleur nulle part.
- Revue visuelle du 2026-10-29 : 16 favoris, dont 10 Z-Image, 4 Klein, 2 Animagine, 0 Juggernaut, 0 Wan. **Z-Image Turbo retenu comme modèle image principal**, Klein en second choix rapide, Animagine pour l'anime. Juggernaut écarté (supprimé). Détails : `style-ladder/NOTES.md`.
- Vitesse Z-Image (2026-10-30) : décodage groupé + 8 seeds par job → ~40-48 s/image contre 163 s (×3,4), images identiques au bit près. Job ≈ 56 s fixes + 33 s/image (+66 s si nouveau prompt).
- Piège de banc ComfyUI : un KSampler à entrées identiques est servi depuis le cache, donc il faut des seeds neuves à chaque job.

## Production : pub MÉTRIQUE 60 s (`metrique-ad/`)
Keyframes Wan 2.2 5B en T2I → I2V Wan 2.2 5B (10 plans) + LTX 2B (1 plan) → RIFE ×2 → 4x-UltraSharp → montage Pillow/ffmpeg avec captures réelles de l'app.
- Leçon : avec `--cache-none`, mettre plusieurs plans/seeds dans **un seul graphe** (chargement des ~17 Go de modèles mutualisé).
- I2V Wan 5B : ~10 min par plan de 2 s, ~16 min par plan de 3 s (480×832, 20 steps). LTX 2B : 74 s pour 1 s.
- Upscale 4x-UltraSharp : ~3 s/frame sur la 3060 Laptop — prévoir ~45 min pour 30 s de rushs.
- Détails et verdicts : `metrique-ad/NOTES.md`.

## Texte → 3D en quads pour Blender (`text-to-3d/`, 2026-10-26)
Klein 4B (image de référence) → TRELLIS.2 int8 en **pipeline 512** (nœuds natifs ComfyUI) → Blender 5.2 : voxel remesh 1/160, QuadriFlow, UV, bake PBR → GLB et .blend en quads (8-12 k, 100 % de quads).
- Environ 9 à 11 min par objet : image 2,5 min, 3D 5 à 7 min, quads 30 s. VRAM max 4,8 Go.
- La cascade 1024 fait OOM sur 6 Go (décodage VAE). Patch `comfyui/custom_nodes/trellis2_lowvram/` (MLP découpé), utile mais insuffisant pour la 1024.
- Pixal3D : textures plus fidèles, mais objet incliné selon la caméra de la référence → option, pas défaut. Hunyuan3D écarté (budget, forme seule en natif).
- ComfyUI relancé le 2026-10-26 avec les mêmes options, logs dans `comfyui/comfy_3d.log`. Ne pas lancer Blender (Windows) pendant une génération : WSL prend 14 Go sur 15,6.
- Détails, bugs QuadriFlow et réglages : `text-to-3d/NOTES.md`.


## Banc vidéo du 2026-10-31 (`video-bench/`)
Keyframes Z-Image/Klein → Wan 5B Q8 I2V (Wan T2I écarté), RIFE ×5 puis 1 frame sur 4 pour 30 fps, 4x-UltraSharp conservé, et Wan Animate 14B Q3 enfin testé : passe sur 6 Go (VRAM 5,6 Go), bon transfert d'expression sur portrait, 339 à 904 s. Chiffres, verdicts et limites : `video-bench/NOTES.md`.

## Court-métrage de nuit : Animagine contre Z-Image dans la chaîne complète (`night-short/`, 2026-11-01 → 02)
Storyboard + time sheet → keyframes → Wan Q8 → upscale anime ×2 → isnet → composite sur décor ×2 → montage 19 s en 1248×1824. Deux films avec les mêmes plans : `v3.mp4` (Animagine) et `v4.mp4` (Z-Image).
- **Z-Image gagne en fiabilité** : même tenue, même ruban et même visage sur 4 plans, visage tenu dans Wan à petite taille, mains lisibles. **Animagine garde le style préféré** mais demande ~4 graines de tri par plan et perd nez et bouche à petite taille.
- Technique de studio validée : **cycle × trajectoire** (un cycle de marche de 30 frames déplacé en perspective = 5 s de marche sans dérive). Marche de profil toujours impossible avec Wan 5B (pied d'appui fixe, 4 clips).
- 27 clips Wan en 141 min cumulées, 10 retenus. Détails, comparaisons et verdicts : `night-short/NOTES.md`, `studio-techniques/NOTES.md`.

## Court-métrage 10 s en rendu 3D stylisé : « Le gardien » (`lighthouse-short/`, 2026-11-05 → 06)
Hybride Blender + IA : extérieurs (phare, mer, faisceau, bateau) en **Blender 5.2 Cycles, décor 100 % scripté** + bateau TRELLIS.2 ; plans du gardien en **Z-Image → Wan 5B I2V → UltraSharp** ; allumage de la lampe, pluie et feu du bateau en compositing ; bande son procédurale. Film : `lighthouse-short/out/final.mp4`.
- **Blender Linux dans WSL** (`lighthouse-short/tools/`) : Cycles CUDA fonctionne, EEVEE non (pas d'OpenGL GPU dans WSL). Évite la famine de RAM du Blender Windows. 8-10 s/frame en 1024×576, 22-27 s/frame en 1080p natif.
- **IA pure écartée pour les plans larges scénarisés** : lampe allumée malgré le prompt, personnages inventés, faisceau qui sort du bateau. **Wan v2v sur rendu 3D écarté** : il invente des lumières et lisse la géométrie ; corriger la scène à la source vaut mieux.
- **Identité entre plans** : très gros plan = recadrage de la keyframe du plan moyen + img2img Z-Image 0,6 (ré-éclairage), plutôt qu'une nouvelle keyframe en texte (dérive cartoon).
- **UltraSharp** : gain net sur les plans IA, quasi nul sur un rendu Cycles débruité → rendu natif 1080p pour Blender.
- **Un seul utilisateur du GPU à la fois** : Cycles + ComfyUI en parallèle font passer Blender de 10 à 75 s/frame.
- Détails : `lighthouse-short/NOTES.md`.
