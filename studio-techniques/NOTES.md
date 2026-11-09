# Techniques d'animation des studios pro, appliquées à notre pipeline

Rédigé le 2026-11-01, avant le test vidéo de plusieurs secondes avec Animagine.
Objectif : repartir de la façon dont les studios fabriquent une image animée, puis choisir ce qui se reproduit sur 6 Go de VRAM.

Fiabilité : **[S]** = relevé dans une source (liens en bas). **[C]** = connaissance générale du métier, non vérifiée par une source ici. À confirmer avant d'en faire une règle.
Les sources trouvées sont surtout des blogs et des forums. Seules l'interview de Waki (ANN) et le glossaire ANN sont solides. Les points [C] sont les plus utiles et les moins sûrs.

## 1. La chaîne d'un studio d'anime 2D, étape par étape

| Étape pro | Ce qu'elle produit | Équivalent chez nous | État |
|---|---|---|---|
| Scénario → **storyboard** | Plans, durée, intention [S] | Rien. On génère puis on regarde. | **Absent** |
| **Layout** | Cadrage, mouvement du perso, décor, hors-champ [S] | Cadrage décidé à la génération (webtoon-layers : « le cadrage se décide à la génération ») | Fait à la main, tard |
| **Time sheet (X-sheet)** | Tableau image par image : quel dessin sur quelles frames, mouvements de caméra, calques [C] | Rien | **Absent** |
| **Genga** (dessins clés) | Poses extrêmes qui portent le mouvement [S] | Keyframe Animagine | OK |
| **Douga / nakawari** (intervalles) | Dessins entre les clés [S] | Wan 5B I2V (il fait les intervalles) | OK, instable |
| Nettoyage, finition, couleur | Trait propre, couleurs [S] | Inutile (Animagine sort déjà fini) | Gratuit |
| **Fonds (BG)** | Décor peint, souvent plus large que le cadre [C] | Décor Animagine vide | OK |
| **Satsuei** (photographie / compositing) | Assemblage des calques, lumière, flou, fumée, étalonnage [S] | `compose.py` (ombre de contact, étalonnage) | Partiel |
| Montage, son | Rythme des plans | Rien | **Absent** |

Constat : on a reconstruit le milieu de la chaîne (clés → intervalles → calques → composite) et sauté le début (storyboard, layout, time sheet) et la fin (montage). C'est ce qui explique les échecs de webtoon-layers : marche de profil qui ne traverse pas, cadrage raté, personnage coupé. Ces erreurs se règlent au layout, pas à la génération.

## 2. Économiser les dessins : l'animation limitée

Les studios de TV n'animent jamais tout. Chaque technique ci-dessous est un moyen de montrer du mouvement avec peu de dessins. Elles sont toutes réutilisables pour nous, car notre ressource rare est le temps de calcul (~215 à 330 s par clip de 2 s).

- **Cadence : doubles et triples [S].** À 24 i/s, « sur 2 » = un dessin pour 2 images (12 dessins/s), « sur 3 » = 8 dessins/s. L'anime TV est surtout sur 3, avec des passages sur 2 ou sur 1 pour l'action forte. Cadence moyenne plutôt que règle fixe.
  - Nos mesures : Wan sort déjà de l'animation « en deux » (écart alterné 2,0 / 0,4, 12 dessins/s, `front_s12`). C'est conforme au style et on n'a rien à ajouter.
- **Poses tenues (holds) [S]** : une pose reste à l'écran. Courant en dialogue. Ça marche si la pose est claire et soutenue par le son ou la caméra.
- **Cycles [S]** : un mouvement court (marche, geste répété, respiration) dessiné une fois et bouclé.
- **Animation partielle [S]** : seule une partie bouge (bouche, yeux, bras). Le reste est figé. Renforcé par clignements, léger mouvement de tête, caméra [S].
- **Mouvements de caméra sur image fixe (pan, zoom) [S]** : le mouvement vient de la caméra qui glisse sur un grand fond. Demande un fond **plus grand que le cadre** et net [C].
- **Poupée / découpage [S]** : le personnage est découpé en pièces réutilisables. Proche de notre approche par calques.
- **Réemploi de plans (banque d'images) [C]** : même plan réutilisé dans plusieurs épisodes (transformations, lancements). Non vérifié, la source consultée n'en parle pas.

### Ce que ça change pour « plusieurs secondes »
Wan 5B I2V ne tient pas un plan de plus de ~2 s sans dérive d'identité (webtoon-layers : « au-delà, l'identité dérive »). La réponse des studios n'est pas de faire un plan long, c'est de **construire la durée avec des plans courts, des cycles et des poses tenues**. Quatre leviers, du moins cher au plus cher :
1. **Boucler** un clip de 2 s en cherchant la paire de frames la plus proche (cycle). 0 s de génération en plus.
2. **Tenir** la pose finale avec micro-mouvements (clignement, cheveux), caméra qui glisse lentement sur un fond large.
3. **Enchaîner 2 à 4 plans** de ~2 s avec cadrages différents (large, moyen, gros plan). Chaque plan repart d'une keyframe Animagine.
4. **Chaîner par la dernière frame** (I2V sur la dernière frame du clip précédent). Le plus risqué : l'erreur s'accumule. À mesurer, pas à supposer.

## 3. Principes de mouvement (Disney, 12 principes) [S]

Source secondaire, mais la liste est standard : écrasement-étirement, anticipation, mise en scène, pose à pose / en continu, chevauchement et prolongement (follow-through), ralenti-accéléré, arcs, action secondaire, timing, exagération, dessin solide, attrait.
Utile pour nous comme **grille d'évaluation** d'un clip, pas comme consigne de génération :
- **Arcs** : un mouvement hors arc paraît saccadé [S]. Bon test sur le bras qui se lève.
- **Chevauchement** : le bras finit son geste après le corps [S]. Cheveux, jupe, ruban doivent suivre avec retard.
- **Anticipation** : petit mouvement préparatoire avant le grand [S]. Wan en fait rarement ; à tester dans le prompt (« crouches slightly before jumping »).
- **Smear** : image floue/étirée pour un mouvement très rapide [S]. À limiter, car trop de smears brouille l'image [S]. Chez nous, un smear apparaît comme une déformation : à distinguer d'une dérive.
- **Frames d'impact** : une ou deux images très stylisées pour un coup [S]. Pas pour ce test.
- **Sakuga** : quelques images de qualité nettement supérieure, placées là où ça compte [S]. Principe à retenir : **concentrer le budget sur le plan fort**, pas sur tous.

## 4. Compositing (satsuei) : ce que les pros font au dernier étage

Source : interview de Kentaro Waki, directeur photo (SAO Alicization) [S].
- Le compositing assemble données de finition, fonds et éléments 3D, suivant les instructions du réalisateur et la time sheet.
- **Interaction de lumière** : un faisceau doit agir sur ce qu'il touche (le Gundam reflète la lumière, l'exposition change là où le tir arrive). Les calques doivent « exister dans le même écran ».
- **Fumée / effets au contact** : les effets naissent quand deux calques interagissent. Ils ancrent l'image dans la scène.
- **Garder le trait du dessinateur** : Waki n'adoucit pas les contours en post pour conserver leur « irrégularité ».
- **Filtre de diffusion (glow) : évité par défaut**, utilisé seulement avec une raison artistique. Il le décrit comme « appliquer une solution sans avoir identifié le problème ».
- **Étalonnage couleur** réglé avec le chef coloriste et le directeur artistique, sur l'image finale, pour que perso et fond tiennent ensemble.
- Principe directeur : **« Ne pas sur-produire »**. Compositing discret, contraste concentré sur les plans forts.

Pour nous : c'est la confirmation de ce qu'on a déjà gagné à la main (ombre de contact, étalonnage ombre/soleil). Ça interdit aussi le réflexe « ajouter du glow ou du grain pour cacher les défauts ». Chaque effet doit corriger un défaut identifié, mesuré.
Non couvert par les sources : bloom, profondeur de champ, tremblé de caméra, parallaxe multiplan, grain. [C] : les studios font de la parallaxe en empilant les calques de fond à des vitesses différentes, et un léger tremblé de caméra pour l'impact. Non vérifié.

## 5. Point technique à tester : la marche sur fond qui défile [C]

Dans webtoon-layers, la marche de profil « sur place » a été jugée inutilisable : le pied d'appui reste fixe dans le cadre, donc un fond qui défile le fait glisser.
En animation pro, un cycle de marche destiné à un fond qui défile n'est pas dessiné « sur place » : **le pied d'appui est dessiné en train de reculer dans le cadre, à la vitesse exacte du défilement**. Le fond est ensuite glissé à cette vitesse. Aucun patinage.
Conséquences à tester (hypothèse, pas résultat) :
- Mesurer la vitesse horizontale du pied d'appui sur un clip Wan de profil (déjà fait pour le pied « fixe » : y 741 → 748).
- Si un clip a un pied qui recule régulièrement, régler le défilement du fond sur cette vitesse. Sinon, c'est le prompt (« camera tracks the character, background scrolls ») qui doit le produire.
- Alternative moins risquée : ne pas montrer les pieds (cadrage à la taille), ce que les studios font aussi pour économiser. Attention : on a déjà écarté ce cadrage en post (source trop petite). Il faut le décider au layout et générer à cette échelle.

## 6. Ce qu'on retient pour le test de cette nuit

Chaque ligne indique le gain attendu et comment le mesurer, comme l'exige CLAUDE.md.

| Technique | Pourquoi | Mesure |
|---|---|---|
| Storyboard + layout + time sheet écrits **avant** de lancer | Évite les plans ratés (profil, coupe, cadrage) | Nombre de clips jetés, comparé aux 5 essais de webtoon-layers |
| Plans courts (~2 s) montés en séquence | Wan dérive au-delà | Dérive d'identité par plan (crops visage) |
| Cycle bouclé sur un clip existant | Durée gratuite | Écart entre la dernière et la première frame de la boucle |
| Pose tenue + animation partielle + pan sur fond large | Durée gratuite, sans dérive | Qualité visuelle ; netteté du pan (fond ≥ 832×1216) |
| Compositing : ombre de contact, étalonnage, rien d'autre | Déjà validé | Réutiliser `compose.py` tel quel |
| Contrôle des **doigts** sur la keyframe ET sur les frames du clip | Critère éliminatoire de l'utilisateur | Crops des mains sur 1 frame sur 6 |

## 7. Questions ouvertes
- Les cadences réelles d'un épisode d'anime TV et la durée moyenne d'un plan : non sourcées ici. À chercher avant de caler le montage sur un chiffre.
- Existence et usage exact de la « banque d'images » : non confirmés.
- Bloom, profondeur de champ, tremblé, parallaxe : aucune source solide trouvée. À tester en comparaison A/B, pas à adopter par principe.

## Sources
- [Interview Kentaro Waki, directeur photo de SAO Alicization (ANN)](https://www.animenewsnetwork.com/interview/2019-01-09/sword-art-online-alicization-director-of-photography-kentaro-waki/.140449) : la plus solide pour le compositing.
- [Glossaire ANN : « Shot on threes (ones, twos, etc.) »](https://AnimeNewsNetwork.com/encyclopedia/lexicon.php?id=61)
- [Limited animation : définition et techniques (Pixune)](https://pixune.com/blog/what-is-limited-animation/) : holds, cycles, animation partielle, pans.
- [Pipeline 2D complet (Pixune)](https://pixune.com/blog/2d-animation-pipeline-2/), [Genga (Bulbapedia)](https://bulbapedia.bulbagarden.net/wiki/Genga), [Inbetweening basics (Clip Studio)](https://tips.clip-studio.com/en-us/articles/954) : étapes et vocabulaire.
- [Spider-Verse : cadence variable (SIGGRAPH)](https://history.siggraph.org/learning/fitting-variable-rate-animation-into-a-modern-feature-film-pipeline-by-oskarsson-and-chazot) et [Slashfilm](https://www.slashfilm.com/562748/into-the-spider-verse-technique) : mélange de 1, 2 et 3 selon le personnage ; cheveux et tissu laissés sur 1 car sur 2 ils sautent.
- [12 principes (CG Wire)](https://blog.cg-wire.com/12-principles-animation/), [Smears (CG Wire)](https://blog.cg-wire.com/smear-frames/), [Frames d'impact (Know Your Meme)](https://knowyourmeme.com/memes/cultures/impact-frames) : sources secondaires.

## 8. Retour d'expérience de la nuit du 2026-11-01 (détails dans `../night-short/NOTES.md`)

| Technique de studio | Verdict sur notre chaîne | Mesure |
|---|---|---|
| Storyboard + layout + time sheet avant de générer | **Retenu.** Un seul plan raté par type de plan au lieu de 5 essais à l'aveugle, sauf pour le profil. | 19 clips Wan générés, 5 retenus ; le profil (4 clips) reste le seul plan sans solution. |
| Plans courts montés en séquence | **Retenu.** Chaque clip dure ~2 s, le film en dure 19,5. | Aucune dérive d'identité à l'intérieur d'un plan. |
| **Cycle × trajectoire** (un cycle bouclé, déplacé sur un chemin en perspective) | **Retenu pour les marches vers/depuis la caméra.** 5 s de marche à partir de 30 frames Wan. | Période mesurée par silhouettes normalisées ; couture à 2,59 contre 1,68 entre frames consécutives. Ne marche pas quand le sujet grossit trop dans le clip (Z-Image, écart 4,7). |
| Chaînage par dernière frame | **Utilisable sur 2 clips, avec dérive.** Hachures sur la jupe dans le 2e clip, rectangle de fond en fin de clip. | À préférer : cycle × trajectoire. |
| Pose tenue + animation partielle | **Retenu** pour le gros plan : le clignement et le souffle viennent de Wan, la durée vient de l'aller-retour (4,4 s à partir de 2 s). | Pas de dérive ; aucun dessin supplémentaire. |
| Pan / travelling sur grand fond | **Retenu**, avec le décor passé en ×2 (RealESRGAN anime) : recul de caméra de 3 s sur le décor seul, poussée de 12 % sur la marche. | Net à l'écran en 1248×1824. |
| Upscale ×2 anime des frames Wan | **Retenu** : traits des yeux et des chaussures nets, aucune déformation. | 3 s/frame sur GPU libre. |
| Éclairage par frame (ombre → soleil, ombre portée) | **Retenu**, interpolé selon la position des pieds. | Ombre portée encore trop floue au soleil. |
| Compositing sobre (« ne pas sur-produire ») | **Suivi** : pas de glow ni de grain. Seuls effets : ombre de contact, étalonnage, pétales en calque. | |
| **Cycle de marche avec pied qui recule** (fond qui défile) | **Infirmé pour Wan 5B** : le pied d'appui reste fixe dans le cadre (0,52 px/frame sur `side_s22`). Le profil reste hors de portée. | `foot.py`. |
| Filtre de diffusion / bloom, tremblé de caméra, parallaxe multiplan | **Non testés** : aucune source solide, pas de gain identifié. | |
