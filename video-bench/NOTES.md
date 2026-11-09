# Banc vidéo : keyframes, I2V, post-traitement, Animate (session du 2026-10-31)

But : vérifier si une meilleure keyframe améliore l'I2V Wan 5B Q8, simplifier le post-traitement, et tester Wan Animate 14B.
ComfyUI lancé avec `--lowvram --disable-pinned-memory --cache-none`. Scripts courts, seed fixée, un job par modèle/prompt.

## A. Keyframes : Wan T2I vs Z-Image vs Klein (608×1056, seed 101)
Commande : `python3 kf.py zimage klein wan` → `kf/<modèle>/<prompt>_s101.png`, planche `kf_sheet.png` (`sheet.py`), journal `kf.log`.
Prompts : `portrait` (gros plan photo), `walk` (plan large, rue pavée, vélos), `anime` (webtoon, plan large).

| Modèle | portrait | walk | anime | VRAM max |
|---|---|---|---|---|
| Z-Image Turbo Q5 | 83 s | 123 s | 145 s | 5,0 Go |
| Klein 4B Q8 | 59 s | 84 s | 105 s | 4,9 Go |
| Wan 5B Q8 (T2I) | 123 s | 157 s | 165 s | 4,7 Go |

(1er job de chaque modèle inclut le chargement ; pas de moyenne en régime établi, un seul seed.)

Verdict visuel :
- **Wan T2I écarté pour les keyframes** : rendu postérisé avec trame de demi-teintes, cadrages incohérents (le plan « walk » montre le personnage de dos, retourné), plus lent que Klein.
- **Z-Image** : meilleur réalisme (peau, rue, lumière), portrait et marche naturels.
- **Klein** : presque aussi bon, ~30 % plus rapide, compositions centrées ; meilleur en anime (trait propre, silhouette complète).
- Aucune main visible dans ces plans : le contrôle des doigts n'a pas pu être fait ici.

## B. Keyframe → Wan 2.2 5B Q8 I2V (480×832, 49 frames = 2 s, 20 steps, seed 7)
Commande : `python3 i2v.py zimage:portrait zimage:walk wan:portrait wan:walk klein:anime` (un seul graphe, modèles chargés une fois). Clips dans `clips/<modèle>_<prompt>/` (PNG 24 fps) et `.mp4`, planche `clips_sheet.png` (`strips.py`).
- 5 clips en **1275 s, soit 255 s par clip de 2 s**. Pic VRAM 5,96 Go, RAM 8,5 Go, swap 2,3 Go. Aucun OOM.
- `zimage_walk` : marche naturelle, rue et vélos stables, **mais le visage se déforme en marchant** (nez, bouche, sourcils fondus sur les frames ~12 à 36, visible dans `preview/zimage_walk_face.png`). Visage petit dans le cadre (~40 px) : Wan 5B ne tient pas l'identité à cette échelle. Relecture initiale erronée, corrigée sur retour utilisateur.
- `zimage_portrait` : sourire et clignement, cheveux mobiles, identité tenue ; un clignement un peu appuyé en milieu de clip.
- `klein_anime` : trait net, tenue et visage stables, **mais le personnage ne marche pas** (retour utilisateur : il reste en place, c'est surtout le cadrage qui bouge). Erreur de relecture corrigée ; la marche anime reste à résoudre (prompt de mouvement, ou chaîne `webtoon-layers/`).
- `wan_portrait` / `wan_walk` : mouvement correct, mais la postérisation et la trame des keyframes Wan T2I restent dans la vidéo.
- **Verdict : la qualité de la keyframe se transmet à l'I2V, mais ne suffit pas : un visage petit se déforme en mouvement (plan de marche). Z-Image (réaliste) et Klein (anime) retenus pour les keyframes, Wan T2I écarté** (plus lent et moins bon, pour le même coût I2V).
- Limite : un seul seed et un seul prompt de mouvement par plan ; pas de test de doigts (mains hors cadre).

## C. Post-traitement (clip `zimage_walk`, 49 frames, 24 fps)
### C1. RIFE : sélection de frames actuelle vs multiple exact de 30 fps (`rife.py`)
Chaîne actuelle : RIFE ×2 → 48 fps → frame la plus proche pour 30 fps (écarts 2,1,2,1,2,2…). Alternative : RIFE ×5 → 120 fps → une frame sur 4 (30 fps exact). RIFE 4.7, fp16, ensemble, fast_mode.
Mesure sur 60 frames à 30 fps : jitter = écart-type / moyenne des différences entre frames consécutives (plus bas = mouvement plus régulier).

| Variante | Jitter | max/moyenne |
|---|---|---|
| 24 fps, frame la plus proche (sans RIFE) | 0,695 | 2,28 |
| RIFE ×2 + sélection (actuel) | 0,461 | 2,13 |
| **RIFE ×5 + 1 frame sur 4 (exact)** | **0,354** | **1,92** |

- RIFE ×2 et ×5 ensemble : 33 s pour 49 frames. Coût négligeable.
- Verdict : **RIFE ×5 puis 1 frame sur 4 retenu** (−23 % de jitter vs actuel, gratuit). La sélection ×2 est conservée seulement si on reste en 48 fps.
- Limites : mesure sur un seul clip, aucun visionnage fluide humain ; le jitter inclut la variation naturelle du mouvement, seul l'ordre relatif compte.

### C2. Upscale 480×832 → 1080×1920 : 4x-UltraSharp (+Lanczos) vs Lanczos seul (`up.py`)
Recadrage 9:16 puis upscale ; UltraSharp = ×4 puis Lanczos vers 1080×1920. Planche de crops : `up/zimage_walk_crop.png`.
| | énergie de détail (passe-haut) | variation temporelle du détail / énergie |
|---|---|---|
| Lanczos | 4,244 | 1,353 |
| 4x-UltraSharp | 5,707 (+35 %) | 1,377 (+1,8 %) |
- Temps UltraSharp : **2,8 s/frame** (~47 min pour 1000 frames).
- Visuel : gain net sur les tissus (plis de la veste), les cheveux, les boutons et les objets du décor ; pas de halo visible. **Défaut** : le visage paraît « peint » ; la cause principale est la déformation déjà présente dans le clip I2V (voir B), UltraSharp l'accentue.
- Scintillement : pas de hausse mesurable.
- Verdict : **UltraSharp conservé** (priorité qualité, gain visible, pas de flicker). Piste non testée : mélange 70/30 avec Lanczos sur les zones de visage.

## D. Wan 2.2 Animate 14B Q3_K_M (GGUF 8,6 Go) : transfert d'expression sur portrait (`animate/`)
**Pourquoi le test du 05/10 avait échoué** : la vidéo de pilotage (`driving_10-15s.mp4`, 480×576, 16 fps, 5 s) est un gros plan d'une personne qui parle, buste seulement. Le squelette de corps pleine hauteur n'a pas de sens ici ; ce qui compte est le crop de visage (`face_images`), net et lisible. Les pieds à plat observés étaient donc attendus.
Chaîne : prétraitement (`pre.py`, 42 s : vitpose-l + yolov10m ONNX CUDA, crop visage, squelette) → `UnetLoaderGGUF` Q3_K_M + LoRA lightx2v I2V 14B rank64 (force 1,2) → `ModelSamplingSD3` shift 5 → `WanAnimateToVideo` (référence = keyframe Z-Image portrait, `clip_vision_h`, VAE wan 2.1) → `SamplerCustomAdvanced` lcm/simple, 4 steps, cfg 1, seed 42. Script : `animate/gen_animate.py`.

| Test | Résolution | Frames (16 fps) | Temps total (chargements + prétraitement inclus) | VRAM / RAM / swap max |
|---|---|---|---|---|
| t1 | 320×576 | 21 (1,3 s) | 387 s | 5,58 Go / 8,1 Go / 2,3 Go |
| t2 | 480×832 | 21 (1,3 s) | 643 s | 5,20 Go / 9,0 Go / 2,6 Go |
| t3 | 320×576 | 77 (4,8 s) | 904 s | 5,17 Go / 11,0 Go / 3,1 Go |

Sorties : `animate/out/gen_<test>_*.png` et `t1.mp4`, `t2_hires.mp4`, `t3_long.mp4` (16 fps). Planche : `animate/cmp_t1_t2_t3.png`.
- **Wan Animate 14B Q3 passe sur la 3060 6 Go** : aucun OOM, VRAM max 5,6 Go, RAM max 11 Go sur 14 (swap 3 Go pour la plus longue). L'inconnue du début de session est levée.
- Le transfert d'expression est convaincant : bouche, yeux, inclinaison de la tête suivent le pilote, l'identité de la référence tient (veste, coupe, décor) y compris sur 77 frames sans dérive visible.
- 480×832 (t2) : plus de détail sur la peau et les cheveux, pour 1,7× le temps de t1. Coût d'une seconde de vidéo : ~300 s/s en 320×576 (t1), ~490 s/s en 480×832 (t2), ~190 s/s en 77 frames (t3, le chargement du modèle est amorti).
- Défauts observés : une main parasite entre dans le cadre en bas à gauche vers la fin de t3 (vient de la vidéo de pilotage) ; clignement appuyé en milieu de clip (reprend celui du pilote) ; le visage est recadré plus serré que sur la keyframe d'origine.
- Limite : un seul pilote (visage de face, gros plan), un seul seed, une seule référence. Pas testé en pied : aucun pilote de corps entier disponible.

### D4. Avec ou sans squelette (`pose_video`) : t1 vs t4 (320×576, 21 frames, même seed)
| | Cadrage | Expression | Temps |
|---|---|---|---|
| t1 avec squelette retargeté | visage recadré bien plus serré que la keyframe | bouche et yeux très marqués | 387 s |
| t4 sans squelette (visage seul) | **cadrage de la keyframe conservé** (tête, épaules, rue) | amplitude de bouche un peu plus faible, tête inclinée sur la 1re frame | 339 s (−12 %) |
- Planche : `animate/cmp_t1_t4.png`. Pour un buste qui parle, le squelette n'apporte pas de gain d'expression (c'est le crop visage qui pilote) et il modifie le cadrage.
- **Verdict provisoire : sans squelette par défaut pour les bustes** (cadrage fidèle à la keyframe, plus rapide). À confirmer sur d'autres seeds et références (un seul seed ici). Le squelette reste à tester pour du corps entier.

## Conclusions de la session (2026-10-31)
| Étape | Décision |
|---|---|
| Keyframes | **Z-Image Turbo** (réaliste) et **Klein 4B** (anime, 30 % plus rapide). **Wan T2I écarté** (postérisé, plus lent). |
| I2V | Wan 2.2 5B Q8 conservé, 255 s par clip de 2 s ; la qualité de la keyframe se transmet à la vidéo. |
| Interpolation | **RIFE ×5 puis 1 frame sur 4 pour 30 fps** (jitter −23 % vs ×2 + sélection), coût négligeable. |
| Upscale | 4x-UltraSharp conservé (+35 % de détail, pas de flicker), 2,8 s/frame ; visage un peu sur-accentué. |
| Wan Animate 14B Q3 | **Utilisable** pour du transfert d'expression sur portrait : 339 à 904 s selon résolution et durée, VRAM 5,6 Go. |
Reste à faire : tester Animate sur d'autres seeds, une référence anime (Klein) et un pilote corps entier ; tester le mélange UltraSharp/Lanczos sur les visages ; un LTX plus récent (téléchargement à valider).

### Retour utilisateur sur les aperçus (2026-10-31)
- `zimage_portrait` : « rend très bien » → validé. `zimage_walk` : **le visage se déforme** → non validé (plan large avec visage petit).
- `klein_anime` : ne fait pas marcher le personnage → pas validé pour l'animation de marche.
- Keyframes Wan T2I : ne convainquent pas → écarté, confirmé.

### Conséquence : plan large avec personnage qui marche
Pas de pipeline validé pour le réaliste en plan large (visage < ~60 px) : Wan 5B I2V déforme le visage. Pistes à tester : plan plus serré (buste/mi-corps) ; résolution I2V plus haute ; réparation du visage après coup (détecter le visage, régénérer ou restaurer image par image) ; Animate 14B avec un pilote de corps entier ; LTX 2B comparé sur le même plan.
