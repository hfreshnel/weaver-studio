# Court-métrage de nuit (2026-11-01 → 02) : Animagine + Wan + calques, avec les techniques de studio

Contexte : test « plusieurs secondes » demandé le 2026-11-01 à 22h30, échéance 5 h. Techniques de référence : `../studio-techniques/NOTES.md`.
Environnement : ComfyUI `--lowvram --disable-pinned-memory` (env `comfy`), Animagine XL 4.0 pour les images, Wan 2.2 5B Q8 pour l'I2V, chaîne de calques de `../webtoon-layers/`.
Scripts : `kf.py` (keyframes), `w.py` (clip Wan), `up.py` (upscale RealESRGAN anime 6B ×4 puis Lanczos ×0,5 = ×2).

## Storyboard et time sheet (24 i/s)

Scène : la collégienne dans la rue de webtoon-layers (`decor_street_00002_`, point de fuite (381, 685), horizon y 685). Récit : elle arrive, sourit sous les cerisiers, repart.

| Plan | Durée | Cadrage / caméra | Technique studio | Source |
|---|---|---|---|---|
| S1 établissement | ~3 s | Décor seul, recul depuis la canopée vers le plan large, pétales qui tombent | Pan/zoom sur grand fond, fond ×2 net, FX en calque | Décor ×2 + FX pétales |
| S2 arrivée | ~2 s | Plan large fixe, elle marche vers la caméra | Calques perso/décor, ombre de contact, étalonnage | `front_s12` (acquis) |
| S3 sourire | ~3 s | Gros plan visage, fond de cerisiers flou | Animation partielle (clignement, cheveux), pose tenue, cycle bouclé | Wan I2V close-up |
| S4 départ | ~4 s | Plan large fixe, elle s'éloigne vers le point de fuite | Plans enchaînés (chaînage par dernière frame), perspective mesurée | Wan I2V de dos |
| S5 sortie | ~2 s | Rue vide, pétales | Pose tenue, mouvement de caméra lent | Décor ×2 + FX |

Total visé : 14 à 16 s. Plans supplémentaires si le temps le permet (plan moyen en pose tenue, etc.).

## Journal

### 23h00 : keyframes et premiers clips
- Keyframes Animagine (même tags de personnage, fond vert), 4 graines par plan, tri à l'œil. **Cohérence entre plans : partielle.** Le gros plan (graine 4) et la vue de dos (`back31` n°3) gardent bob noir, ruban rouge, yeux ambre, col marine. Les premières vues de dos étaient des 3/4 ou doublaient le personnage ; il a fallu des négatifs (« looking back, from side, face ») et « facing away, back focus ». Le plan de face d'origine (`green_girl`, cravate rouge, ruban en serre-tête) ne correspond pas aux nouveaux plans : régénéré (`front51` n°2) avec les mêmes tags que le dos.
- Plan « mid » (buste, regarde les pétales) : les deux mains sont douteuses (doigts fusionnés ou illisibles). **Mains hors cadre par recadrage** (haut du corps seul) plutôt que rejeter la keyframe : le cadrage décide ce qu'on voit.
- Wan Q8, 49 frames, graine 11 : dos 227 s, gros plan 255 s, ~4 min par clip tous jobs confondus quand la file est vide.
- Dos (`back_s11`) : l'identité tient sur 2 s, elle rapetisse en perspective correcte (R² 0,989, K 1,287, horizon implicite y 389).
- Chaînage par dernière frame (`back_chain`, graine 12) : l'identité tient, mais la jupe se couvre de hachures à partir de la frame ~10 et un rectangle de fond de teinte différente apparaît en fin de clip. À juger au composite.
- Gros plan graine 12 : elle sourit et ferme les yeux en fin de clip (fermés à partir de la frame ~32 et jusqu'à la fin). La graine 11 ne cligne pas dans les frames échantillonnées.
- **Upscale anime ×2 (RealESRGAN 6B, ×4 puis Lanczos ×0,5) contre Lanczos seul**, sur 3 frames du gros plan : traits bien plus nets (contour des yeux, cils, ruban), aucune déformation vue. Coût mesuré : 3 s/frame sur GPU libre. **Retenu pour tous les clips** (49 frames ≈ 2,5 min), mesuré en situation de file occupée : plusieurs minutes de latence, car les jobs attendent derrière Wan.
- Placement automatique (`shot.py`) : ajuste hauteur = K × (pieds − h0) sur le clip, aligne h0 sur l'horizon du décor (685) et l'axe de marche sur le point de fuite (381), échelle choisie par la position de départ des pieds. **Reproduit le réglage manuel de `front_walk2` à 0,2 % près** (échelle 1,302 contre 1,3, décalage (43, 410) contre (44, 409)) : le calcul à la main est supprimé.
- Éclairage par frame : étalonnage ombre → soleil et ombre portée selon la position des pieds dans le décor (mélange lissé entre y 985 et y 905).
- Pétales (`lib.py`) : calque procédural, 34 pétales à profondeur variable, mouvement sur 2. Utilisé en S1 et S5.

### 23h40 : montage v0 et technique « cycle × trajectoire »
- **Montage v0** (`v0.mp4`, 17,3 s, 415 frames) : S1 + S2 (ancien clip, tenue différente) + S3a + S3 + S4 + S5. Sert de référence ; l'identité du perso varie encore entre S2 et le reste.
- **Chaînage par dernière frame vs cycle × trajectoire (dos).**
  - Chaînage (`back_s11` + `back_chain`, 93 frames = 3,9 s) : aucune coupure détectée à la jonction (`jumps.py`), mais la jupe se couvre de hachures dans le 2e clip et il faut jeter les 4 dernières frames (rectangle de fond).
  - **Cycle × trajectoire** (`cycle.py`, technique de studio : un cycle de marche bouclé, déplacé sur un chemin en perspective) : période de marche mesurée par distance de silhouettes normalisées = 30 frames (1,25 s, deux pas), départ frame 6 (écart 2,59, contre 1,68 entre deux frames consécutives : la couture est dans la variation normale). Le sprite est remis à une taille canonique (hauteur ajustée K × (pieds − h0)), puis replacé à chaque frame avec l'échelle de la trajectoire Z(t) = Z0 (1 + v t). Vitesse prise sur le clip lui-même (0,168 × la distance initiale par seconde), donc la foulée colle au déplacement.
  - Résultat : **6 s (144 frames) de marche sans aucune dérive d'identité**, car seules 30 frames de Wan servent. Aucun coût de génération en plus. Les coutures (tous les 30 frames) tombent sur un changement de dessin, pas sur une tenue. **Retenu pour S4.** Limite : le mouvement se répète toutes les 1,25 s, naturel pour une marche mais visible sur un geste non périodique.
  - Sur le plan de face, la période est moins nette (écart 4,9 : le sprite grandit et son visage change) ; à surveiller.
- Despill par teinte (`despill2.py`) : le fond aqua (140, 234, 188) laisse des franges cyan dans les cheveux, les chaussures et le tissu blanc, que `G = min(G, max(R, B))` (vert pur) ne retire pas. Désaturation des pixels à ±28° de la teinte du fond. Gain visible mais modeste.
- Plan de face : le visage perd nez et bouche quand le sujet est petit (~40 px de tête) : Wan ne dessine pas de détails à cette taille. Piste testée : générer plus grand (toile 62 % au lieu de 42 %) puis réduire au composite, ce que permet le placement par trajectoire.

### 00h20 : plan de face, définition finale, montage v1
- **Plan de face : 5 clips Wan comparés** (même keyframe `front51` n°2, 49 frames, 4 à 6 min chacun).
  | Clip | Sujet à l'entrée | Résultat |
  |---|---|---|
  | `front_s12` | 42 % de la toile | Approche très rapide, yeux qui virent au vert dès la frame 30, fond qui change de teinte à la fin. Écarté. |
  | `front_s13` (prompt « very slowly ») | 42 % | Bras tendu parasite frames 10–20, yeux bruns puis rouges. Écarté. |
  | `front_s14` | 42 % | Marche propre mais tête de ~40 px : **nez et bouche disparaissent**, yeux qui tournent au rouge. Utilisable de loin seulement. |
  | `frontL_s15` (62 %, « stays the same size ») | 62 % | Visage net, mais **bras écartés et mains aplaties**, inutilisable (mains). Écarté. |
  | `frontL_s16` (même prompt) | 62 % | S'arrête de marcher après la frame 10 : le prompt « stays the same size » fige le personnage. Écarté. |
  | **`frontL_s17`** (62 %, bras le long du corps) | 62 % | Marche régulière, yeux ambre stables sur 49 frames, mains pas dans le champ. **Retenu.** |
  | `frontL_s18` | 62 % | Marche correcte, peau qui rosit en fin de clip (dérive). Écarté. |
  Leçon : **plus le sujet est grand dans la toile Wan, plus le visage tient**, et ce n'est plus gênant, car le placement par trajectoire (`cycle.py`) réduit le sprite au composite. Les prompts qui parlent de taille (« stays the same size ») figent le mouvement.
- **S2 = `frontL_s17` en cycle × trajectoire** : période 32 (même parité de « doubles » ; 33 donnait un écart plus faible mais fait changer la phase), départ frame 12, vitesse −0,08 de la distance par seconde (le clip approche naturellement à −0,125). 72 frames (3 s). Le visage reste minimaliste (yeux, pas de bouche lisible) à cette taille : c'est le plan le plus faible, mais il est lointain.
- **Définition finale ×1,5** (1248×1824) : décor ×2 réduit, sprites ×2 : les traits du décor et des chaussures sont nets là où la version 832×1216 les adoucit. Implémenté par `NS_F=1.5` (`lib.py`, `comp.py`). À vérifier : coût du rendu.
- **Montage v1** (`v1.mp4`, 20,5 s) : S1 3 s, S2 3 s, S3a 2 s, S3 4,4 s, S4c 5 s, S5 2 s ; pétales procéduraux en continu sur S2 et S4c.
- Gros plan « mid » : le clip Wan a généré **ses propres pétales**, saturés et énormes, qui recouvrent la tête dès la frame 30. Régénéré sans mention de pétales dans le prompt (graines 12 et 13), les pétales venant du calque FX.

### 00h35 : plan de profil (échec) et vitesse du pied d'appui
- Protocole 3 : keyframe de profil `side61` n°2 sur une **toile paysage 832×560** (la toile portrait de 512 px de large avait servi d'excuse aux essais précédents), elle à gauche, prompt « traverse le cadre de gauche à droite ».
  - `side_s21` (412 s) : elle ne traverse pas, **elle pivote** vers la caméra, bras écartés, puis revient. Écarté.
  - `side_s22` (384 s) : vraie marche de profil, bras le long du corps, mais **sur place** : la toile paysage ne change rien. Écarté pour la traversée.
- Test de l'hypothèse « cycle de studio avec pied qui recule » (`foot.py`, sur `side_s22`) : pied d'appui sur les frames 11 à 30, vitesse **0,52 px/frame**, alors qu'un cycle de studio destiné à un fond qui défile aurait un pied qui recule d'environ la vitesse de défilement. **Le pied d'appui de Wan reste fixe dans le cadre**, comme dans les clips précédents. Hypothèse (section 5 de `../studio-techniques/NOTES.md`) **infirmée pour Wan 5B** : aucun défilement de fond ne peut coller aux pieds. Le profil reste hors de portée de cette chaîne ; la marche de face et de dos (déplacement dans la profondeur) fonctionne, car la perspective du sol absorbe la vitesse.
- Coûts mesurés : Wan Q8 49 frames = 227 à 411 s (médiane ~285 s), upscale ×2 de 49 frames = 100 à 240 s quand la file est chargée (3 s/frame seul), matting isnet 1,4 à 2,3 s/frame sur CPU, rendu d'un plan composite 49 à 144 frames = 1 à 3 min sur CPU.

### 01h25 : montage v3 (Animagine, 1248×1824, 19,5 s)
Chaîne retenue pour `v3.mp4` : `kf.py` (Animagine, 4 graines, tri à l'œil) → `w.py` (Wan Q8, 49 frames) → `upclip.py` (RealESRGAN anime ×2) → `layer.py` (isnet-anime) → `despill2.py` (teinte, ±42°) → `cycle.py` (cycle × trajectoire, perspective, ombre de contact, étalonnage ombre/soleil, pétales) ou `closeup.py` (fond de cerisiers flou) → `zoomshot.py` (travelling avant) → `montage.py` (coupes sèches, fondu d'entrée 6 frames et de sortie 12).
| Plan | Durée | Source Wan (frames utiles) | Technique |
|---|---|---|---|
| S1 | 3 s | aucune | Recul de caméra sur décor ×2 (zoom 1,5 → 1,0), pétales |
| S2 | 3 s | `frontL_s17`, 32 frames bouclées | Cycle × trajectoire (vers la caméra) |
| S3a | 2 s | `mid_s13`, 49 frames | Buste sur fond flou |
| S3 | 4,4 s | `close_s12`, 49 frames en aller-retour + 10 frames tenues | Pose tenue + animation partielle (le clignement vient de Wan) |
| S4 | 5 s | `back_s11`, 30 frames bouclées | Cycle × trajectoire (s'éloigne) + travelling avant 1,0 → 1,12 |
| S5 | 2 s | aucune | Poussée lente sur rue vide, pétales |
Au total : **5 clips Wan retenus sur 19 générés**, soit ~25 min de génération Wan utile pour 19,5 s de film, et ~100 min de Wan au total pour les essais jetés (dont profil : 4 clips pour rien).
**Défauts connus :**
- Cohérence du personnage entre plans : bonne sur la silhouette et les couleurs, mais **le ruban change** (nœud sur la tête en S3a, ruban pendant sur le côté en S3 et S2) et le col marine devient bleu-vert au gros plan. Animagine + tags ne suffit pas à tenir une fiche personnage sur 4 images.
- S2 : visage minimaliste (yeux sans pupille lisible, ni nez ni bouche), car le sujet fait ~50 px de tête dans le cadre.
- S4 : franges cyan résiduelles sous la jupe, ombre portée au soleil encore floue à la fin.
- Mains : jamais dans le champ pendant le film (gros plan recadré au buste, marches avec bras le long du corps).

### 02h00 : comparaison Z-Image Turbo dans la chaîne (plan de face)
- 4 keyframes Z-Image (prompt en langage naturel, même description du personnage) contre 4 d'Animagine (tags) : **Z-Image garde la même tenue, la même cravate et les mêmes proportions sur les 4 graines** ; Animagine change de cravate, de ruban et de col d'une graine à l'autre. Mains relâchées, poings lisibles, doigts non fusionnés. Le style est celui d'un anime TV années 90–2000 (yeux bruns, ombrages doux), pas celui, plat, d'Animagine.
- Clip Wan Q8 du plan de face à partir de la keyframe Z-Image (`zfront_s31`, 338 s, même toile à 62 % et même prompt que `frontL_s17`) : marche stable, **le visage (yeux, nez, bouche) tient jusqu'au bout**, ce que les clips Animagine perdaient à cette taille. Elle avance peu (pieds 1000 → 1023), mais c'est une marche lente crédible.
- Cycle impossible à caler (écart minimal 4,7 à toute période, contre 0,84 entre frames consécutives) : le sprite grossit trop pendant le clip. Placement direct (`shot.py`, 46 frames) à la place.
- Dans le décor Animagine, le raccord de style passe : le décor reste en aplats, elle est plus « télévisée », ce qui se voit surtout de près.

### 03h45 : montage v4 (Z-Image) et bilan de la nuit
**v4** (`v4.mp4`, 18,6 s, 1248×1824) : mêmes plans et même chaîne que v3, mais keyframes Z-Image Turbo (prompts en langage naturel, une description commune du personnage). Même décor Animagine.
- Plans : S1 et S5 identiques à v3 ; S2 = `zfront_s31` + `zfront_chain` (91 frames, placement direct) ; S3a = `zmid_s61` ; S3 = `zclose_s41` en aller-retour ; S4 = `zback_s52` (frames 12 à 46) + `zbackchain_s53` (80 frames, placement direct).
- Z-Image n'a pas pu servir au cycle × trajectoire : ses clips Wan grossissent trop ou restent statiques (écart de cycle 4,66 à 4,7 contre 0,73 à 0,84 entre frames). Le plan de dos reste immobile ~12 frames au départ (retirées) ; le chaînage ajoute des blocs de couleur dans le fond du 2e clip, sans effet après détourage.

| Critère | v3 : Animagine (tags) | v4 : Z-Image (langage naturel) |
|---|---|---|
| Cohérence de la tenue et de la coiffure entre les graines | Faible (cravate, ruban et col changent, doublons de personnage) | **Forte** (même uniforme, même cravate, même ruban sur les 4 graines) |
| Cohérence entre les plans du film | Ruban qui change, col marine → bleu-vert | **Visage, ruban et uniforme identiques** sur 4 plans |
| Visage à petite taille dans Wan (plan large) | Nez et bouche disparaissent, yeux qui virent | **Visage conservé** jusqu'au bout du clip |
| Mains | Fusionnées ou illisibles sur 3 keyframes sur 12 | Poings relâchés lisibles, aucun problème vu |
| Mouvement obtenu de Wan | Clignement, cheveux, cycle de marche périodique (cycle × trajectoire possible) | Très stable mais **peu de mouvement** (pas de clignement sur 2 graines), cycle impossible |
| Vue de dos | Vraie vue de dos après négatifs | 3/4 arrière, tête tournée (pas de dos pur sur 8 graines) |
| Rendu | Webtoon, plat, très « Animagine » (le look que l'utilisateur aime) | Anime TV années 90–2000, plus doux, moins graphique |
| Temps d'une keyframe | 25 à 30 s | 40 à 130 s à froid (modèle à recharger quand Wan occupe le GPU) |

**Verdict provisoire :**
- Pour la **fiabilité d'un film** (même personnage sur 4 plans, visage tenu, pas de mains ratées), **Z-Image est nettement supérieur**. Animagine demande un tri sévère et des plans recadrés pour cacher ses défauts.
- Pour le **style** que l'utilisateur préfère, Animagine reste la référence ; le test ne tranche pas cette préférence, il la chiffre : ~4 graines de tri contre ~1.
- Piste à tester : keyframe Z-Image → conversion au style Animagine (img2img à bas denoise) pour garder la cohérence de Z-Image et le trait d'Animagine. Non testé.

**Chiffres de la nuit (22h30 → 03h45, tout en arrière-plan) :**
- 27 clips Wan Q8 de 49 frames générés (141 min de calcul cumulées, médiane ~5 min ; 10 retenus sur 2 films). 8 jobs d'upscale de keyframes (batches de 4) et ~30 jobs d'upscale ×2 de clips.
- VRAM : ~4,6 Go occupés pendant Wan (mesuré à 22h40), RAM du processus ComfyUI 5,1 Go à vide de session (GGUF + encodeurs), 6 Go utilisés sur 13 Go en fin de nuit.
- Une file ComfyUI chargée allonge toutes les durées (l'upscale de 49 frames est passé de 100 s à 1400 s derrière deux jobs Z-Image). Ne pas lancer de jobs de familles différentes en parallèle : ils s'entrelacent et rechargent leurs modèles.

**Retenu :** storyboard avant génération ; plans courts ; cycle × trajectoire pour les marches périodiques ; pose tenue + aller-retour ; décor ×2 et sprites ×2 (RealESRGAN anime) ; rendu final ×1,5 ; despill par teinte ; éclairage par frame ; recadrage pour masquer les mains.
**Écarté :** profil (4 clips, 2 protocoles) ; défilement de fond avec cycle de marche (pied d'appui fixe dans Wan : 0,52 px/frame) ; chaînage comme moyen principal d'allonger un plan ; « stays the same size » dans un prompt Wan (fige le personnage) ; mention de pétales dans un prompt Wan (pétales énormes et saturés).

**Pour rejouer :** `kf.py <shot>` ou `zk.py <shot>` → `w.py` ou `zjob.sh` → `cycle.py` / `shot.py` / `closeup.py` → `zoomshot.py` → `montage.py v3|v4 <plans>` avec `NS_F=1.5`. Les mattes sont dans `layers/`, les journaux dans `logs/`, les fiches de contrôle dans `kf/`.
