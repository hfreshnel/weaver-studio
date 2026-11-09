# MÉTRIQUE — pub de lancement verticale 60 s (v1, muette)

Sortie : `out/metrique_launch_v1.mp4` (H.264 High, 1080×1920, 30 fps, ~60 s, yuv420p, faststart, sans audio).
Plan de production complet (storyboard, prompts, angle) : voir le plan validé ; cue-sheet son : `SOUND.md`.

## Pipeline
1. `gen.py kf …` : keyframes Wan 2.2 TI2V 5B en T2I (length=1), 480×832, 3 seeds par plan, un seul graphe par plan.
2. `selected.json` : keyframe retenue par plan + boîtes de surlignage des captures.
3. `gen.py i2v …` : I2V Wan (ou LTX pour P02), plusieurs plans par graphe (chargement des modèles mutualisé), RIFE ×2 intégré → 48 fps.
4. `upscale.py` (env conda `comfy`) : 48 → 30 fps, recadrage 9:16, 4x-UltraSharp, 1080×1920 → `clips_final/<plan>/`.
5. `compose.py` : montage déterministe Pillow → ffmpeg (textes Inter, logos officiels, captures réelles en mockup, étalonnage par séquence, transitions).

## Modèles / réglages
- Wan 2.2 TI2V 5B fp16 + umt5-xxl fp8 + VAE wan2.2 : 480×832, 20 steps, cfg 5, uni_pc/simple, shift 8, 24 fps.
- LTX-Video 2B 0.9.8 distilled fp8 + T5-XXL fp8 : 512×896, 8 steps (LTXVScheduler), cfg 1, euler, 24 fps.
- RIFE 4.7 (ComfyUI-Frame-Interpolation), 4x-UltraSharp (67 Mo).
- ComfyUI : `python main.py --lowvram --disable-pinned-memory --cache-none`.

## Temps mesurés (RTX 3060 Laptop 6 Go, 14 Go RAM)
- Keyframe seule : 82–151 s (dominé par le rechargement des ~17 Go de modèles à chaque job avec `--cache-none`).
- 3 keyframes dans un seul graphe : ~380–470 s ; ~870–1000 s quand deux files tournent en parallèle (inutile : le GPU est sérialisé).
- I2V Wan, 2 plans × 49 frames (+RIFE) dans un graphe : 1207 s (~10 min/plan de 2 s).
- I2V LTX, 25 frames (+RIFE) : 74 s.
- I2V Wan, 3 plans (49+73+73 frames, +RIFE) dans un graphe : 2517–2692 s (~16 min par plan de 3 s ; ~50 s/step à 73 frames).
- I2V Wan, 2 plans × 73 frames : 1819 s.
- Upscale 4x-UltraSharp fp16 (script autonome, image par image) : ~3,1 s/frame → 834 frames en ~45 min ; VRAM ~4,5 Go.
- Montage `compose.py` (1800 frames 1080×1920, Pillow → x264 preset slow CRF 18) : 5 min 43 s.
- Total génération IA (keyframes + I2V + upscale) : ~4 h 30 en arrière-plan.

## Verdicts I2V
- P01 jet d'eau + main : dynamique, bon hook (main plus claire que le reste du casting, masqué par l'étalonnage froid).
- P02 (LTX) : pouce qui défile, écran sans texte ; léger écart de teinte pouce/main, acceptable sur 1 s.
- P03/P06/P10 cliente : identité stable sur toute la durée, aucun glitch visage.
- P04 billets : geste fluide, billets non lisibles (voulu).
- P05 : une silhouette entre dans le champ sur les 0,2 dernières s → coupée (`--trim-end 0.2`).
- P07/P08 plombier : stable ; P08 légère variation de coiffure de la cliente en milieu de clip.
- P09 (keyframe = illustration du site) : mains et clé crédibles, très cohérent avec la fiche service.
- P11 : motos en golden hour, mouvement propre.

## Export (vérifié avec ffprobe)
h264 High, 1080×1920, 30/1 fps, yuv420p, 1800 frames, 60,000 s, 55 Mo, sans piste audio.
Contrôles : planche-contact 1 image/2 s, rendu « zones sûres » (aucun texte hors x 90–940 / y 220–1500 sauf le téléphone qui déborde volontairement en bas), aperçu 360×640 lisible.

## Verdicts keyframes
- Bible personnage tenue sans LoRA : la cliente (blouse wax moutarde/navy, cheveux courts) est reconnaissable sur P03/P06/P08/P10 ; le plombier (combinaison navy, t-shirt gris) cohérent sur P07/P08 et avec l'illustration plomberie du site (réutilisée comme keyframe de P09).
- P04 v1 ratée (mains blanches, dollars, costume) → prompt corrigé (mains ouest-africaines, billets FCFA) + négatifs ciblés : OK.
- P05 v1 sans tableau électrique → prompt plus concret (« grey metal breaker box, door open, loose wires ») : OK.
- P11 : rue golden hour crédible, architecture un peu générique.

## Audit vs CLAUDE.md (2026-10-21) : étapes non encore justifiées par une comparaison
- Keyframes en Wan T2I (~130 s/image) : jamais comparé à un SDXL réaliste (~20 s/image) ni à un SD 1.5.
- LTX pour P02 : choix non documenté. Un 2e jeu de modèles rien que pour 1 s de vidéo.
- RIFE x2 puis rééchantillonnage 48 → 30 fps par sélection de frames : écarts irréguliers (2,1,2,1,2,2,1…) donc micro-saccades probables. Non comparé à une sortie 24 fps native, ni à RIFE vers un multiple exact de 30.
- 4x-UltraSharp (45 min) : upscale x4 puis réduction à ~x2,3 en Lanczos. Non comparé à Lanczos seul ni à un modèle x2. Scintillement image par image non évalué.
- `--cache-none` : ajouté en même temps que `--disable-pinned-memory` lors du correctif OOM, jamais testé séparément. Il coûte le rechargement de ~17 Go à chaque job.

## Captures de démo (stack locale + seed)
Données fictives (Rodrigue Agbo, plombier ; Afi Dossou, cliente), aucun avis seedé, mention « données de démonstration » à l'écran.
Ajustements nécessaires, tous hors repo ou sur l'instance locale uniquement :
- `seed/compose.override.yml` : WAF contourné (port 80 occupé par un Apache de l'hôte + conflit `default.conf` dans l'image reconstruite), backend exposé sur :8000, `KEYCLOAK_ISSUER=http://localhost:8080/realms/metrique`.
- Keycloak local : rôles realm `client`/`provider`, web origin `http://localhost:3000` et mapper d'audience `metrique-backend` sur le client `metrique-frontend` (sinon CORS sur /token puis 401).
- Playwright : user-agent mobile standard + `navigator.webdriver=false`, sinon le front se croit en prérendu et désactive Keycloak.
- `backend/.env` créé depuis `.env.exemple` (gitignoré).
Parcours réels joués dans l'UI : commande (Confort), acceptation par le prestataire, page de paiement, messagerie aller-retour.

## 2026-10-24 : fp16 supprimé
`wan2.2_ti2v_5B_fp16.safetensors` a été supprimé, remplacé par `Wan2.2-TI2V-5B-Q8_0.gguf` (qualité équivalente, job −35 %, voir `webtoon-layers/NOTES.md`).
Pour relancer `gen.py`, remplacer dans `wan_graph` le node `UNETLoader` par `{"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "Wan2.2-TI2V-5B-Q8_0.gguf"}}`.
