# Webtoon : animation par calques (personnage détouré + décor fixe)

Chaîne testée : keyframe Animagine sur fond vert → Wan 2.2 5B I2V (512x752, 49 frames, 20 steps) → détourage → despill → incrustation sur un décor Animagine vide (`decor_street_00002_.png`).
Scripts : `matte.py <méthode>`, `despill.py <méthode>`, `evaluate.py <décor> <méthodes…>` (env conda `matting`, isolé de `comfy`).
Résultats : `eval/edges.png` (contours sur magenta), `eval/comp_<méthode>.mp4` (incrustations).

## Génération
- Keyframes fond vert (Animagine, 3 en un seul job) : 79 s. Le fond sort **vert pastel** (191,229,176), pas un vert de chroma key, malgré le prompt.
- L'image source contient déjà du vert renvoyé par le fond (reflets dans les cheveux, ombres de la jupe) : aucun détourage ne peut l'enlever, il faut un despill.
- Wan sur fond vert : 396 s pour 49 frames. Le fond reste uni et stable. Geste des bras parasite en fin de clip.
- Décor vide (Animagine, 2 en un seul job) : 107 s, propre, même style que le personnage.

## Comparaison des détourages (mêmes 49 frames)
| Méthode | Temps | Variation du masque (flips) | Verdict |
|---|---|---|---|
| chroma key (distance couleur + démélange) | 0,08 s/frame | 1,60 % | Écarté : 3 correctifs ajustés à la main nécessaires (taches parasites, intérieur translucide, seuils liés à la couleur du fond), contours plus durs. Garde son intérêt comme repli rapide. |
| **isnet-anime** (rembg, CPU) | **1,45 s/frame** | **1,44 %** | **Retenu** : masque le plus stable, aucun réglage, insensible à la couleur du fond. ~70 s par clip de 2 s, négligeable face aux ~400 s de Wan. |
| birefnet-general (rembg, CPU) | 90 s/frame | 1,48 % | Écarté : trait légèrement plus net en zoom x2, invisible à l'échelle finale, pour un coût 60x supérieur (73 min par clip de 2 s). |
| despill `G = min(G, max(R,B))` | 0,05 s/frame | — | **Retenu**, quelle que soit la méthode : supprime les reflets verts de la source. |

- Chroma brut : 6 % de l'intérieur du personnage semi-transparent (ombres gris-vert de l'uniforme proches du fond pastel), contre 1,5 à 2 % pour isnet et birefnet. Corrigé par un remplissage de l'intérieur, mais c'est un réglage de plus.
- Chemin retenu : **Wan sur fond uni → isnet-anime → despill → incrustation**.

## Calques vs une seule passe (bilan provisoire)
- Le décor est parfaitement fixe et réutilisable. Le style du personnage colle à celui du décor.
- En qualité brute, il n'y a pas de gain visible par rapport à Wan direct sur la rue (`comfyui/output/wan_walk49.mp4`), où le décor restait déjà stable. L'intérêt des calques est ailleurs : réutiliser les décors, contrôler la caméra au montage, refaire le personnage seul.
- Il manque encore : une ombre au sol (le personnage flotte), l'harmonisation de la lumière, et un décor qui défile quand le personnage marche (sinon effet « moonwalk »).

## Test `--cache-none` vs cache par défaut (2026-10-24)
ComfyUI 0.42 : le cache par défaut n'est plus le cache « classique » mais `--cache-ram` (éviction sous pression RAM).
Banc : `bench_cache.sh <label> <flags>` + `bench_cache.py`. Une session webtoon type est rejouée, résultats dans `bench/`.
Les 6 jobs : Animagine perso s1, perso s2, décor s3 → Wan I2V 25 frames s7, s8 → Animagine perso s4.
A = `--lowvram --disable-pinned-memory --cache-none` ; B = `--lowvram --disable-pinned-memory` (cache-ram).

| Job | A (s) | B (s) |
|---|---|---|
| anim perso s1 (à froid) | 38 | 83 |
| anim perso s2 (même prompt) | 42 | **30** |
| anim décor s3 | 53 | 56 |
| wan s7 (changement de modèle) | 294 | 176 |
| wan s8 | 254 | 223 |
| anim perso s4 (retour) | 76 | 69 |
| **Total** | **758** | **639** |
| Pic RAM système / swap | 5,1 Go / 1,3 Go | 4,0 Go / 1,0 Go |
| Pic RSS ComfyUI / VRAM | 3,4 Go / 5,96 Go | 3,3 Go / 5,5 Go |

- Aucun OOM ni erreur avec B : le crash du 20/10 venait donc du pinned memory, pas du cache.
- Les modèles sont mappés en mmap (« dynamic VRAM loading … Staged ») et relus depuis le cache disque du noyau. Le rechargement coûte donc peu, même avec `--cache-none` : les ~17 Go rechargés à chaque job (noté pendant la pub MÉTRIQUE) ne se vérifient plus avec cette version.
- Seul gain net et attendu : un job qui reprend le même prompt saute l'encodage texte et le rechargement (30 s contre 42 s, −29 %). Pour les autres jobs, l'écart reste dans le bruit d'une mesure unique : le 1er job à froid est plus lent en B à cause de l'état du cache disque.
- Le temps d'un step Wan varie de 3 s à 48 s dans un même job : le modèle fp16 de 9,5 Go est streamé RAM → VRAM. C'est ça qui domine la variance, pas le cache.
- Sorties : Wan identique (écart max de 2/255). Animagine identique à froid (s1, s4) ; s2 et s3 ont la même composition avec des micro-détails différents (pétales, traits fins). L'encodage texte mis en cache diffère numériquement d'un encodage recalculé, et le sampler ancestral amplifie l'écart. Ce n'est pas une perte de qualité, mais la reproductibilité au bit près n'est pas garantie entre les deux modes.
- **Verdict : `--cache-none` écarté.** Il n'apporte rien en mémoire et coûte du temps dès qu'on enchaîne des jobs similaires. Nouvelle commande : `python main.py --lowvram --disable-pinned-memory`.
- Piste ouverte par ce test : Wan 5B en fp8 ou GGUF Q8 (~5 Go) tiendrait presque en VRAM et réduirait le streaming. C'est probablement le levier n°1 pour la vitesse.

## Wan 2.2 TI2V 5B : fp16 vs GGUF Q8_0 (2026-10-24)
Modèle : `QuantStack/Wan2.2-TI2V-5B-GGUF`, `Wan2.2-TI2V-5B-Q8_0.gguf` (5,4 Go) dans `comfyui/models/unet/`, chargé par `UnetLoaderGGUF`.
Clip testé : celui du webtoon (fond vert, `green_girl.png`, 512×752, 49 frames, 20 steps, seed 7). Lancement avec `--lowvram --disable-pinned-memory`.
Bancs : `BENCH=bench_wan_quant.py ./bench_cache.sh <label> <flags>`, avec `MODE=steady` pour 3 jobs Q8 enchaînés. Résultats dans `bench/Q_*` et `bench/S_*`.

| Variante | Sampling | Job complet | Pic RAM / swap | RSS ComfyUI |
|---|---|---|---|---|
| fp16 (2 jobs) | 13,4–14,9 s/step | 325–339 s | 3,8–5,9 Go / 0,7–1,8 Go | 2,8–4,5 Go |
| Q8, 1er job (chargement GGUF) | 6,0–6,7 s/step | 268–318 s | 9 Go / 0,8 Go | 8,2–9,7 Go |
| **Q8, jobs suivants** | **6,4–7,2 s/step** | **211–235 s** | 10 Go / 0,8 Go | 8,8 Go |
| Q8 + umt5 GGUF Q5_K_M | 7,3 s/step | 562 s | 13,8 Go / 3,8 Go | 12,6 Go |

- Sampling ×2 plus rapide. En session (jobs enchaînés), le job complet passe de ~330 s à ~215 s (−35 %). Le 1er job paie ~80 s de chargement du GGUF : contrairement au safetensors fp16, il n'est pas mappé en mmap mais chargé dans la RAM du processus.
- Qualité : visuellement équivalente. Même trajectoire que fp16 avec la même seed (y compris le geste de bras parasite en fin de clip), même trait net, col, ruban et yeux identiques. Scintillement entre frames identique (écart moyen 7,05 contre 7,14). PSNR de 22 dB contre fp16 : léger décalage du mouvement, pas une dégradation (fp16 contre fp16 : 89 dB, déterministe).
- `--lowvram` ou non : aucune différence (3,8 Go de VRAM utilisables et 1,4 Go déchargés dans les deux cas, 215 contre 229 s). On garde `--lowvram`.
- Contrepartie : la RAM du processus monte à ~9 Go (GGUF + encodeur de texte), contre ~3–4 Go en fp16 mmap. Il reste ~4 Go de marge sur 14 Go.
- umt5 GGUF Q5 : **écarté**. La RAM sature (dé-quantification de l'embedding), avec 3,8 Go de swap, et le job prend 562 s. On garde l'encodeur umt5 fp8.
- **Verdict : Wan 5B Q8_0 retenu** à la place du fp16 pour l'I2V du webtoon.
- Il reste ~80 s hors sampling par job (encode + décodage VAE de 49 frames) : c'est la prochaine cible.

## Ménage du 2026-10-24
Supprimés : Wan fp16 (9,4 Go) et umt5 GGUF Q5 (3,9 Go), tous deux écartés ; les sorties des bancs ; les détourages écartés (`matte_chroma*`, `matte_birefnet-general`) ; les frames PNG de `eval/comp_*` (les MP4 sont gardés) ; les doublons dans `comfyui/output/`.
Conservés : `src/` (frames Wan fond vert), `matte_isnet-anime` et `+despill`, `eval/*.mp4`, `eval/edges.png`, `bench/` (journaux et mesures).

## Qualité du composite (2026-10-24)
Scripts : `compose.py --preset <p> [--sheet i,j] [--video]` (presets dans le fichier), `layer.py <prefixe> <dossier>` (isnet-anime + despill en une passe), `gen.py kf|i2v <plan>` (Animagine / Wan Q8 via ComfyUI).
Décor `decor_street_00002_` : point de fuite (381, 685) mesuré par Hough (18 intersections concordantes). Route à l'ombre au bas du cadre (117,121,139), bande ensoleillée y 880–970 (239,211,196).

### Corrections du composite d'origine
- Le recentrage par frame sur la boîte englobante faisait glisser le personnage quand il écarte les bras (boîte 151–368 → 89–460) et les pieds recalés à chaque frame trépidaient. Remplacé par **une transformation fixe par clip** (médianes), la caméra source étant fixe. Retenu.
- Ombre de contact : la version serrée sous les chaussures était invisible (chaussures noires sur route sombre). Élargie ×1,6 et écrasée ×0,25 : visible, ancre les pieds. Retenu.
- Ombre portée (soleil venant de la gauche) : correcte en direction, trop floue pour un rendu en aplats (les ombres du décor ont des bords nets). À durcir si on place un personnage au soleil.
- Étalonnage « à l'ombre » (rapport ombre/soleil de la route) : intègre le personnage dans l'ombre des bâtiments, mais ternit à 0,6. 0,25–0,35 est un compromis, à valider à l'œil.

### Effet tapis roulant : diagnostic
- La source « walks forward in place » est une **marche sur place** : le pied d'appui ne glisse pas (bas des chaussures fixe, y 741 → 748 sur 49 frames). Faire défiler ou zoomer le décor ferait glisser les pieds (moonwalk inversé) ; faire avancer le personnage le ferait patiner. Aucun montage ne rend ce plan juste avec les pieds visibles.
- Cadrage à la taille + travelling arrière (zoom du décor 1,12 → 1,0) : le mouvement passe, mais la source 512×752 agrandie ×2,5 floute le trait et la tête sort du cadre. **Écarté** : le cadrage se décide à la génération, pas au montage.
- **Piste retenue : caméra fixe, le personnage se déplace vraiment dans la source**, avec de la marge (keyframe d'origine réduite sur une toile verte élargie, le fond uni le permet). Les keyframes régénérées avec « small figure, wide shot, distant » changeaient le style et la tenue : écartées.

### Marche de face vers la caméra (`front_s11`, Wan Q8, 264 s)
- Elle avance vraiment et grandit. La perspective est cohérente : hauteur = 1,187 × (y pieds − 225), R² 0,997, écart moyen 4,3 px sur 30 frames → caméra fixe, horizon implicite y 225, caméra à hauteur d'yeux.
- Montage (`front_walk`) : horizon source aligné sur celui du décor, axe de marche aligné sur le point de fuite → échelle 0,987 (pas d'agrandissement), une seule transformation, aucun glissement de pieds.
- Limites : trop rapide (55 % → plus de 150 % en 2 s), seules les frames 0–28 sont exploitables. Au-delà, elle sort du cadre et l'identité dérive en gros plan (col jaune et bleu ciel, marque bleue sur le front).

### Marche de profil (`side_s11`, Wan Q8, 335 s)
- Marche quasi sur place jusqu'à la frame ~35 (pied d'appui fixe ou glissant vers l'avant), puis déplacement réel à la fin. Ni tapis roulant ni traversée : aucun défilement de décor ne peut s'y caler. Personnage coupé à gauche au départ (erreur de cadrage de la toile). **Écarté**, relancé avec un meilleur cadrage et un prompt plus explicite.

### 2e essai (seed 12)
- Profil (`side_s12`, 297 s, personnage entièrement dans le cadre, prompt « traverse tout le cadre ») : toujours une marche sur place, avec en plus des artefacts en rayures sur le fond. **Profil écarté** après 2 seeds et 2 prompts : Wan 5B ne fait pas traverser le cadre sur fond uni en 2 s.
- Face lente (`front_s12`, 321 s, départ à 42 % de la taille, prompt « walks slowly ») : approche lente (pieds y 492 → 536), perspective cohérente (horizon implicite y 212, K 1,064, R² 0,96, écart moyen 2,9 px), identité stable sur tout le clip, aucun geste parasite. Animée « en deux » (écart entre frames alterné 2,0 / 0,4, soit 12 dessins/s), conforme au style anime. Les 2 dernières frames sautent (teinte du fond) : retirées.
- Composite `front_walk2` (échelle 1,3, horizon et axe de marche alignés sur le décor, pieds dans l'ombre des bâtiments du début à la fin, contact 0,85, étalonnage ombre 0,25) : **meilleur résultat à ce jour**. Pieds posés, taille cohérente avec la perspective, aucun glissement visible. Sortie : `eval/front_walk2.mp4` (47 frames, ~2 s).
- **Chaîne retenue pour un plan de marche** : keyframe d'origine réduite sur une toile verte élargie → Wan Q8 caméra fixe, marche lente vers la caméra → `layer.py` → mesure de l'horizon implicite → `compose.py` en placement fixe aligné sur l'horizon et le point de fuite du décor.

### Reste à faire
- Résolution : agrandir ×1,3 adoucit le trait. Générer en 640×944 ou plus coûterait environ ×2 en temps. À comparer avec un upscale anime léger (RealESRGAN anime 6B, ~18 Mo).
- Lumière : étalonnage constant ; il faudrait le moduler quand le personnage passe du soleil à l'ombre (mesurer la couleur du sol sous ses pieds à chaque frame).
- Durcir l'ombre portée pour les plans au soleil.
- Calcul automatique du placement : aujourd'hui l'échelle et le décalage sont reportés à la main après la mesure de l'horizon.
