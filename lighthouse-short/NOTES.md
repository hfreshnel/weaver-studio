# Court-métrage 10 s « Le gardien » : rendu 3D stylisé, 1 personnage humain (2026-11-05 → 06)

Demande (2026-11-05, 22h34, échéance 5 h) : un short de 10 s avec au moins un humain, rendu 3D réaliste dans la forme sans être photoréaliste. Storyboard et réalisation libres, Blender disponible, assets maison autorisés.
Point de départ : `../night-short/` (storyboard + time sheet, Z-Image plus fiable qu'Animagine), `../video-bench/` (Wan 5B Q8 I2V, visage déformé en plan large, UltraSharp), `../text-to-3d/` (Blender en ligne de commande).

## Storyboard et time sheet (16:9, 24 i/s, 240 frames)

Récit : une nuit de tempête, le gardien d'un phare aperçoit un bateau en perdition, allume la lampe, le faisceau trouve le bateau.

| Plan | Frames | Cadrage / action | Source prévue | Pourquoi |
|---|---|---|---|---|
| S1 | 0–59 (2,5 s) | Plan large : phare éteint sur la falaise, tempête, vagues sur les rochers, poussée lente | Blender **contre** Z-Image → Wan | Même phare en S1 et S4 (cohérence), caméra contrôlée ; à comparer avec l'IA |
| S2 | 60–119 (2,5 s) | Plan rapproché poitrine, à travers la vitre ruisselante : il plisse les yeux vers le large | Z-Image → Wan I2V | Visage moyen/grand dans le cadre : là où Wan tient l'identité |
| S3 | 120–167 (2 s) | Très gros plan visage : la lampe s'allume, lumière dorée sur son visage | Z-Image → Wan I2V + montée de lumière en compositing | Effet de lumière piloté en post (contrôlable) plutôt que demandé à Wan |
| S4 | 168–239 (3 s) | Plan large : le faisceau balaie la mer et éclaire le chalutier | Blender **contre** Z-Image → Wan | Faisceau rotatif et mer : point fort d'un rendu 3D |

Règles reprises des sessions précédentes :
- Pas de visage en mouvement à petite taille (Wan 5B le déforme sous ~60 px) : les plans larges ne montrent pas le gardien.
- Mains hors cadre (doigts = critère éliminatoire) ; si une main apparaît, contrôle des doigts au zoom.
- Une description de personnage commune pour toutes les keyframes Z-Image (cohérence prouvée dans `night-short`).

## Résultat et pipeline retenue (lire d'abord)

Film final : `out/final.mp4` (10,0 s, 1920×1080, 24 i/s, H.264 CRF 15 + AAC). Version précédente pour comparaison : `out/v2.mp4`.

```
S1, S4 (extérieurs) : scene.py (Blender 5.2.3 Linux, décor 100 % procédural + bateau TRELLIS.2) → Cycles CUDA natif 1080p
S2 (gardien)        : Z-Image Turbo keyframe 1280×720 → Wan 2.2 5B Q8 I2V 1024×576 (61 f) → 4x-UltraSharp → 1080p
S3 (gros plan)      : recadrage de la keyframe S2 → Z-Image img2img 0,6 (ré-éclairage) → Wan I2V (49 f) → UltraSharp
post.py             : étalonnage, pluie en calque (S1, S4), feu du bateau suivi (S2), allumage + clé chaude (S3), vignette
sound.py            : bande son procédurale calée sur la time sheet (pluie, vent, vagues, tonnerre, lampe, corne, nappe)
```

| Étape | Retenu | Écarté (et pourquoi) |
|---|---|---|
| Extérieurs | Blender seul (contrôle du phare, du faisceau, du bateau, de l'éclair) | Z-Image → Wan : lampe allumée 4/4 en S1, garçon inventé et faisceau sorti du bateau 4/4 en S4. Blender → Wan v2v 0,35 : invente un faisceau quand la lampe est éteinte, lisse la falaise, déforme l'éclairage du bateau |
| Gardien | Z-Image (une description commune) → Wan I2V | Keyframe S2 `s13` : œil blanc en cours de clip |
| Très gros plan | Recadrage S2 + img2img 0,6 (identité garantie) | Keyframes S3 en texte seul : personnage plus cartoon (nez, barbe) ; img2img 0,45 : lumière inchangée |
| Allumage de la lampe | Compositing (rampe froid → or, scintillement, clé chaude) : timing exact | Demander l'effet à Wan (non maîtrisable) |
| Agrandissement | UltraSharp pour l'IA ; rendu natif pour Blender | UltraSharp sur Blender (≈ Lanczos) ; Lanczos sur l'IA (mou) |
| Rendu Blender | Cycles CUDA dans WSL | EEVEE (pas d'OpenGL GPU dans WSL) ; Blender Windows (RAM Windows saturée) |

Pour rejouer : `python3 kf.py s2` → `wan.py` → `i2i.py` → `up.py` ; `tools/blender-5.2.3-linux-x64/blender -b --factory-startup --python scene.py -- renders/lh_v4.blend ../text-to-3d/out/lh_boat/trellis_r512_s42.glb` → `render1080.sh` ; `python sound.py out/sound_v3.wav cues.json` ; `python post.py edit_final.json out/final.mp4 out/sound_v3.wav` (env `comfy`).

## Journal

### 22h35 : mise en place
- ComfyUI relancé (`--lowvram --disable-pinned-memory`, journal `../comfyui/comfy_short.log`).
- **Blender Linux 5.2.3 installé dans `tools/`** (384 Mo, sha256 vérifié) au lieu du Blender Windows. Raison : Windows n'avait que 0,58 Go de RAM libre (2,8 Go de mémoire compressée) avant même de lancer ComfyUI, et WSL peut monter à 14 Go. Le Blender Windows serait parti en swap (déjà constaté dans `../text-to-3d/`). Dans WSL, Blender partage la mémoire de WSL avec ComfyUI.
- Contrainte externe : **débit Internet ~0,3-0,5 Mo/s** ce soir (Blender en ~10 min). Un modèle de plusieurs Go (ex. ControlNet Z-Image, ~3 Go) coûterait 2 h : écarté pour cette nuit.

### 22h40 : keyframes Z-Image 1280×720 (8 steps, une description commune du gardien)
Style demandé : « still frame from a high-end 3D animated feature film, cinematic CGI render, realistic human proportions, slightly stylized ».
- S2, 4 graines : **le même personnage sur les 4** (bonnet marine, sourcils et barbe blancs, ciré jaune, pull torsadé crème). Rendu « film d'animation 3D » réussi : peau en SSS, gouttes sur la vitre, mer visible par la fenêtre. Aucune main dans le cadre.
- Retenues : `s12` (il regarde vers la fenêtre, mer visible) et `s13` (regard inquiet vers la vitre, vagues visibles). Les deux partent en Wan pour comparaison.
- Temps : ~40-60 s par image (premier job avec chargement).

### 22h55 : Blender dans WSL, décor procédural (`scene.py`, `render.py`)
- **EEVEE inutilisable dans WSL** : pas de contexte OpenGL GPU (EGL/zink échouent), repli logiciel, 60 s pour un cube en 640×360. **Cycles CUDA fonctionne** (RTX 3060 vue ; OptiX indisponible, donc débruitage OIDN sur CPU). Choix : Cycles.
- Décor 100 % scripté, reconstruit en ~4 s : promontoire (champ de hauteur avec bruit + déplacement Voronoi), phare (tour conique à bande rouge, galerie, garde-corps, lanterne, dôme), maison du gardien aux fenêtres chaudes, mer (modificateur Ocean animé, écume), ciel d'orage procédural (bruit 4D animé), brouillard, double faisceau tournant à 36°/s, lumière d'appoint sur le bateau au passage du faisceau (tricherie classique de plateau).
- Bugs rencontrés, chacun corrigé :
  1. Image noire : un brouillard dans le *world* s'étend à l'infini en Cycles et absorbe tout le ciel → brouillard homogène dans un cube borné (aussi rapide).
  2. Brume « de jour » : trop de diffusion de la lune → densité 0,0016, lune 0,9, exposition +0,5.
  3. Pas de faisceau (1) : une vitre en *transmission* bloque l'éclairage direct en Cycles → vitre en alpha.
  4. Pas de faisceau (2) : la sphère de l'ampoule entoure les spots → ampoule invisible aux ombres.
  5. Falaise en mur plat → côte en parabole (promontoire) ; pentes étirées → grille 480×340 + déplacement Voronoi.
- Aperçus CPU (25 %, 32 échantillons) : ~15 s/frame. Le faisceau dans le brouillard est réussi ; le ciel et la falaise restent moins riches qu'une image IA.

### 23h00-23h30 : Wan I2V de S2 (1024×576, 61 frames, 20 steps, graine 7)
- Sampling : **12,7 s/step, soit ~4,5 min par clip de 2,5 s** en 1024×576 (16:9 exact), plus ~1 min de décodage VAE. Le temps « mur » affiché (1650-2575 s) inclut l'attente dans la file.
- `s2_s7` (keyframe s12) : il tourne la tête vers la fenêtre puis revient, respiration, barbe et sourcils qui bougent. **Visage net et stable** sur les 61 frames (crops à pleine résolution, frames 1/15/30/45/61). **Retenu.**
- `s2b_s7` (keyframe s13) : plus d'action, il se penche vers la vitre. Mais **œil entièrement blanc vers la frame 40** (regard trop latéral) et visage caché en fin de clip. Écarté (seules les frames 1-30 seraient utilisables).
- Keyframes S3 en texte seul (4 graines) : jolies, mais **le personnage dérive** (nez énorme, barbe plus touffue, style plus cartoon que S2) et le très gros plan n'est pas respecté. → Nouvelle méthode : **recadrage du visage de la keyframe S2 + img2img Z-Image** (denoise 0,45 / 0,6) pour le ré-éclairer en lumière dorée. L'identité est garantie par construction.

### 23h30-23h50 : bateau 3D, plans extérieurs IA contre Blender, S3 en img2img
- **Bateau** : `../text-to-3d/gen.py` (Klein → TRELLIS.2 512), référence Klein excellente (chalutier rouge, cabine blanche, mât). Mesh GLB 200 k faces texturé, **46 min de mur** au lieu de ~7 : le job TRELLIS a attendu dans la file derrière Wan et a tourné pendant les rendus CPU Blender (RAM 12,1 Go, swap 1,4 Go). Importé dans la scène, mis à 11 m. Il flotte : hauteur et tangage suivent un plan ajusté sur la surface Ocean évaluée toutes les 2 frames.
- **Keyframes IA de S1** (4 graines) : plus spectaculaires que Blender (gerbes d'écume, ciel riche), mais **lampe allumée sur 4/4** malgré « lamp is dark and unlit » (le récit exige une lampe éteinte avant S3), phare au ras de l'eau, et un rendu plus « peinture numérique » que CGI. Le phare ne serait pas le même qu'en S4.
- **Keyframes IA de S4** (4 graines) : **échec sur 4/4** : un garçon torse nu inventé sur le pont, faisceau qui part du bateau, échelles incohérentes. → **S4 se fait en Blender** : seul moyen d'avoir le même phare, un faisceau qui tourne depuis la lanterne et un bateau à la bonne échelle.
- Nouvelle piste pour S1/S4 : **rendu Blender (mise en place, caméra, faisceau, bateau) → Wan 5B en vidéo-à-vidéo** (encodage VAE du rendu, re-bruitage partiel à denoise 0,35 / 0,5, `v2v.py`). Hypothèse : Wan ajoute la matière (écume, nuages, rochers) sans perdre le contrôle de la 3D. À comparer au rendu Blender seul.
- **S3** : img2img du recadrage de S2. À denoise 0,45, identité parfaite mais presque aucun changement de lumière. À 0,6, l'identité tient toujours (yeux, sourcils, barbe, bonnet), la lumière devient chaude et douce et la salle de la lampe apparaît derrière lui. Retenu : `d60_s22`. L'allumage franc est fait en compositing (`post.py`, `lightup`), ce qui donne un timing exact sur le son.
- Correction scène : avec les actions en couches de Blender 5, `action.fcurves` n'existe plus et les clés restaient en Bézier (mer et faisceau ralentis aux bords). → interpolation linéaire par défaut dans les préférences avant d'insérer les clés.

### 00h00-00h25 : S3 en vidéo, rendu GPU Blender, montage v0
- **Wan S3** (49 frames, keyframe img2img `d60_s22`) : identité tenue, regard qui se durcit, bouche qui s'entrouvre, et une forte poussée de caméra qui finit sur les yeux (un vrai temps fort). Visage propre. La lumière reste douce : la clé chaude est ajoutée en post. **Job de 11 min**, dont 3,3 min de sampling (9,9 s/step à 49 frames) : le décodage VAE en 1024×576 est l'étape la plus longue.
- **Rendu Blender sur GPU** (Cycles CUDA, 1024×576, 48 échantillons + OIDN) : **8,2 s/frame**, S1 (61 frames) en 8,5 min, S4 (73 frames) en 10 min. ComfyUI est vidé avant (`POST /free`) puis le GPU est rendu à Blender (`renderjob.sh`).
- **Montage v0** (`post.py edit_v0.json`, son `sound_v1.wav`, 10,0 s, 1920×1080, Lanczos sans upscale IA) :
  - la montée de lumière de S3 (froid et sombre → scintillement → clé dorée venant de la droite) fonctionne ;
  - la pluie en calque lie S1 et S4 ;
  - **l'écart de style Blender / IA est le défaut principal** : falaise « fondue », rochers en blobs, reflets blancs plats au premier plan de S4, contre un rendu « film d'animation » pour S2/S3.
  - Erreur de méthode : mon attente de fin de rendu s'arrêtait sur le mot « Error », présent dans un avertissement HIP sans gravité. Le v0 a donc été monté avec S4 incomplet (39/73 frames). Corrigé : attente sur le nombre de fichiers.
- **S4, le bateau ne s'éclairait pas au passage du faisceau** : la lumière d'appoint, placée dans la lanterne et orientée vers le bas, était bloquée par le plancher de la galerie. Je l'ai déplacée de 8 m vers le bateau et passée à 5e6 W (gaussienne de ±6 frames autour de la frame 140), avec un cône de 22°. Le bateau s'illumine franchement, le moment « le faisceau trouve le bateau » se lit. Mer un peu plus rugueuse pour casser les reflets plats.

### 00h25-00h55 : vidéo-à-vidéo Wan sur les rendus Blender, scène v3
- **Coût d'un v2v (61-73 frames, 1024×576)** : ~14 min, dont 5 min de sampling (13-16 s/step). Avec `denoise` < 1, ComfyUI fait quand même les 20 steps : le coût ne baisse pas avec le denoise. Le reste vient de l'encodage et du décodage VAE (RAM 9 Go sur 13, swap 3 Go).
- **S1 à 0,35** : léger gain (crête d'écume au premier plan, lanterne plus détaillée), mais **deux hallucinations contraires au récit** : un faisceau bleu sort de la lampe éteinte, et une petite silhouette apparaît sur les rochers. La falaise reste « fondue », Wan ne corrige pas la géométrie. → **v2v écarté pour S1** ; le job à 0,5 a été annulé.
- **S4 à 0,35** : **le bateau gagne nettement** (détails TRELLIS flous → cabine et fenêtres nettes, coque plus propre), la mer gagne un peu de matière, aucun élément inventé. Gain réel mais modeste.
- **Corrections à la source dans Blender (scène v3)**, moins chères qu'un v2v et sans hallucination :
  - **Falaise** : subdivision simple ×1 avant le déplacement (les flancs n'avaient que ~10 rangées de sommets sur 24 m) + strates rocheuses horizontales et Voronoi dans le relief du shader → roche accidentée, plus de traînées verticales. Coût de rendu inchangé à l'aperçu.
  - **Éclair en ouverture de S1** (frames 5-8) : soleil froid qui scintille et ciel qui flashe. Un premier essai incluant la diffusion du brouillard donnait un blanc laiteux sur plusieurs frames, écarté. Version retenue : éclair exclu du brouillard, ciel ×(1 + 0,6 × intensité).
  - **Bateau caché en S1** (clés de visibilité avant la frame 99) : plus de coque coupée au bord du cadre, plus besoin de recadrer.
- **S2, lisibilité du récit** : ajout en compositing d'un **feu de bateau à l'horizon**, dans la fenêtre (feu de mât blanc chaud + feu de bord rouge). Il oscille avec la houle et suit la dérive de caméra, mesurée par corrélation de phase (OpenCV) sur la zone de la fenêtre. Il apparaît progressivement dès la frame 6.
- **Son v2** recalé sur les nouveaux repères : tonnerre 0,35 s (éclair à 0,21 s), « clac » de la lampe à 5,33 s (début du scintillement de S3), accord majeur à 8,63 s (le faisceau sur le bateau).

### 01h05-01h40 : upscale, v1, scène v4
- **UltraSharp sur les plans IA (S2, S3)** comparé à Lanczos sur le visage de S2 (frame 31, crop 500×500 en 1080p) : sourcils, mèches de barbe, rides et maille du bonnet nettement plus nets, **aucun effet « peint »** sur ce rendu CG (contrairement au réaliste de `video-bench`). **Retenu.** Coût : 7,5 s/frame depuis 1024×576 (×4 → 4096×2304 → 1920×1080).
- **Erreur à ne pas refaire** : lancer l'upscale ComfyUI pendant un rendu Cycles. La VRAM monte à 5,8/6 Go, Blender passe de 10 à 37-75 s/frame, et l'upscale ne produit rien en 3 min. Les deux ont été arrêtés, ComfyUI vidé (`/free`). **Un seul utilisateur du GPU à la fois.**
- **v1** (`edit_v1.json`) : S1 v3, S2 et S3 upscalés, S4 = v2v 0,35 de la scène v2. Le feu du bateau se voit dans la fenêtre de S2 et la clé chaude dore le visage en S3. Le noir d'avant l'allumage en S3 était trop profond par rapport à S2 (saut à la coupe) : niveau « froid » passé de 0,22 à 0,4.
- **S4 v3** : falaise rocheuse OK, mais (1) la lumière d'appoint à 5e6 W / 22° inondait la mer devant le bateau, blanche comme de la neige ; (2) le premier plan de mer restait blanc mat même sans elle (ciel reflété en rasant, élargi par la rugosité 0,12). → **scène v4** : appoint à 2,5e6 W / 11°, spéculaire de la mer 0,6 → 0,3, rugosité 0,05, **clapot** (bruit 4D animé en relief) qui fragmente le reflet. Le premier plan se lit comme de l'eau. La chaîne v2v sur S4 v3 a été arrêtée pour ne pas enrichir un rendu défectueux.
- **Rendu natif 1080p contre 576p agrandi** (S1 frame 30, CPU, 205 s) : le natif est plus net (garde-corps, fenêtres, cheminée) que Lanczos. Comparaison avec UltraSharp à venir. Coût estimé du natif sur GPU : ~35-40 s/frame, soit ~80 min pour S1 + S4.

### 01h50-02h10 : S4 v4, verdict sur le vidéo-à-vidéo
- **S4 v4** (73 frames, 9,4 s/frame) : le bateau s'illumine au passage du faisceau (frames 134-146), clapot au premier plan, plus d'inondation blanche.
- **v2v 0,35 sur S4 v4** contre Blender seul :
  - gain : coque et cabine du bateau plus nettes ;
  - pertes : falaise lissée (moins de détail rocheux) et **moment clé déformé** (bateau éclairé par en dessous au lieu du gréement doré par le faisceau, feu inventé à la proue).
- **Verdict : v2v écarté pour S4 aussi.** S1 et S4 sont en **Blender seul**. Le v2v à 0,5 est annulé : à 0,35, il modifie déjà ce que la 3D contrôle (lumière, événements), et plus de denoise ne peut qu'accentuer cette dérive. Le v2v garde un intérêt pour un rendu 3D pauvre en matière (un objet TRELLIS flou en gros plan, par exemple) ; ici, corriger la scène à la source a été plus efficace (falaise, mer, éclairage).

### 02h10-02h30 : rendu natif contre upscale pour Blender, v2
- **UltraSharp n'apporte presque rien sur les rendus Blender** : sur S1 frame 30, il est à peine plus net que Lanczos. L'image débruitée par OIDN est lisse et il n'y a pas de texture à reconstruire. Le **rendu natif 1080p** est nettement plus net (garde-corps, arêtes, fenêtres). → **S1 et S4 re-rendus en natif 1920×1080** (40 échantillons + OIDN, scène v4) : **27 s/frame sur GPU**, ~60 min pour 132 frames. UltraSharp reste retenu pour les plans IA (S2, S3), où il gagne vraiment.
- **v2** (`edit_v2.json`, son v3 avec la corne du bateau) : le film se lit de bout en bout. Éclair d'ouverture, feu du bateau dans la fenêtre, allumage progressif en S3 (noir froid, scintillement, or), bateau doré par le faisceau, corne en réponse. **Aucune main à l'écran** sur les 240 frames, le contrôle des doigts est sans objet.

### 03h15 : film final
`out/final.mp4` : 10,0 s, 1920×1080, 24 i/s, H.264 CRF 15 + AAC 192 k, 19 Mo. Montage `edit_final.json` = v2 avec S1 et S4 en rendu natif 1080p (S4 : 72 frames en 30 min ; S1 : 60 frames en 22 min, 21-27 s/frame).

**Bilan de la nuit (22h34 → 03h15, tout en arrière-plan)**
- IA : 16 keyframes Z-Image + 4 img2img, 3 clips Wan I2V retenus sur 3 utiles (S2 ×2, S3), 3 v2v (tous écartés), 1 bateau TRELLIS.2, ~300 frames UltraSharp.
- Blender : décor reconstruit 4 fois (v1 → v4), ~25 aperçus CPU (15 s chacun), 266 frames GPU en 576p, 132 frames natives en 1080p.
- Main-d'œuvre GPU perdue : ~5 min de contention Blender/ComfyUI, ~15 min de v2v sur S4 v3 interrompu, 1 v2v S1 annulé.
- Pics : VRAM 5,98 Go (TRELLIS), RAM 12,1 Go + 1,4 Go de swap (TRELLIS pendant les rendus CPU).

**Limites connues du film**
- Écart de style visible entre les plans Blender (décor procédural, rendu de jeu soigné) et les plans IA (rendu de long métrage d'animation). La pluie et l'étalonnage le réduisent sans l'effacer.
- La mer de Blender n'a ni gerbes ni écume sur les rochers (pas de simulation de fluide) : c'est le point où l'IA était meilleure.
- S3 : 2-3 petites taches sombres flottantes près de la joue vers la fin du clip (artefact Wan) ; la clé chaude est un dégradé 2D, pas un vrai ré-éclairage.
- Faisceau : comme un vrai phare, il ne descend pas sur le bateau ; l'éclairage du bateau est une lumière de tricherie synchronisée.
- Bande son jugée au spectrogramme et au niveau RMS uniquement : **pas écoutée**.

**Pistes non testées**
- Simuler les gerbes (particules ou Mantaflow) ou les composer depuis un clip Wan de vagues seules, détourées.
- Personnage en 3D (MPFB / Rigify + mocap BVH) pour un plan large du gardien, ou Wan Animate piloté par un mannequin Blender.
- ControlNet profondeur pour Z-Image (~3 Go, non téléchargé ce soir à cause du débit) : keyframes IA calées sur la géométrie Blender.
