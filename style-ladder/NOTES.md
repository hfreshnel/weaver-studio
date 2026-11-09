# Échelle de styles : du cartoon au photoréalisme (2026-10-25)

But : trouver quel style, et quel modèle par style, donne le meilleur rendu visuel sur la 3060 Laptop 6 Go.

## Protocole
- Même scène pour tout : jeune femme, carré noir, veste rouge, terrasse de café, tasse tenue à deux mains, rue pavée, vélos, lumière de fin d'après-midi, plan moyen (`SUBJECT` dans `gen.py`).
- 8 styles (`STYLES`) : `1_flat`, `2_anime`, `3_bd` (ligne claire), `4_3d` (film d'animation), `5_paint`, `6_semi`, `7_cine` (pellicule 35 mm), `8_photo`. Le style est une phrase placée avant la scène.
- 2 seeds (101, 202) par couple modèle/style. 74 images au total. Animagine ne fait que les styles 1 à 5, avec des tags à la place des phrases.
- Commande : `python3 gen.py animagine wan klein zimage juggernaut`, puis `sheet.py` (planches par style) et `zoom.py <style> [modèles]` (zoom visage et mains). ComfyUI lancé avec `--lowvram --disable-pinned-memory`.
- Sorties : `out/<modèle>/<style>_s<seed>.png`, planches dans `sheets/`, sélection dans `shortlist/`.

| Modèle | Fichiers | Résolution / réglages |
|---|---|---|
| Animagine XL 4.0 | checkpoint 6,9 Go | 832×1216, 25 steps, euler_a, cfg 5 |
| Juggernaut XL v9 (SDXL photo) | checkpoint 7,1 Go | 832×1216, 30 steps, dpmpp_2m karras, cfg 4,5 |
| Wan 2.2 TI2V 5B, T2I (length 1) | GGUF Q8_0 5,4 Go + umt5 fp8 | 704×1280, 20 steps, uni_pc, cfg 5, shift 8 |
| FLUX.2 Klein 4B distillé | GGUF Q8_0 4,3 Go + Qwen3-4B fp8_mixed 5,6 Go + flux2-vae | 832×1216, 4 steps, euler, cfg 1 |
| Z-Image Turbo | GGUF Q5_K_M 5,6 Go + Qwen3-4B fp8_mixed (partagé) + ae | 832×1216, 8 steps, res_multistep, cfg 1, shift 3 |

## Temps et mémoire
Temps par image en régime établi : médiane des jobs de 2 seeds, 1er job de chaque modèle exclu, mesures prises après la fin du téléchargement.

| Modèle | 1er job | Régime établi | VRAM max | RAM / swap max |
|---|---|---|---|---|
| Animagine | 46 s | 41 s (n=2) | 4,9 Go | 4,1 / 0,7 Go |
| Juggernaut | 69 s | **64 s** | 4,9 Go | 8,3 / 6,0 Go |
| Klein 4B | 103 s | **92 s** | 4,9 Go | 8,9 / 5,9 Go |
| Wan 5B T2I | 155 s | 161 s | 4,6 Go | 9,9 / 5,5 Go |
| Z-Image Turbo | 196 s | 163 s | 5,0 Go | 8,4 / 6,1 Go |

- Aucun OOM ni erreur sur les 37 jobs.
- Klein et Z-Image passent très peu de temps à sampler : ~2 s/step × 4 pour Klein, ~4 s/step × 8 pour Z-Image. Le reste part dans les va-et-vient en VRAM : encodeur Qwen3 (5,4 Go) → modèle → VAE. Le décodage VAE décharge le GGUF, qui est réinitialisé à chaque seed (« Model Initialization » de 10 à 46 s). **Piste n°1 de vitesse** : sampler toutes les seeds avant de décoder (batch ou décodage groupé), ou un encodeur Qwen3 plus léger.
- Animagine tournait à ~21 s/image le 20/10, contre 34 à 48 s ici. Ses 3 premiers jobs ont partagé le disque avec le téléchargement, et la RAM était plus chargée par le cache des autres modèles. Pas creusé.

## Verdicts par style (vignettes + zoom visage/mains)
| Style | Meilleur | Remarques |
|---|---|---|
| 1 flat | Klein, Z-Image | Klein : aplats francs et contours épais, nez dessiné maladroitement. Z-Image : plus minimaliste. Wan correct. Animagine ignore le style et reste anime. Juggernaut fait de l'illustration, pas du flat. |
| 2 anime | Animagine, Klein | Animagine reste la référence du trait anime. Klein : propre, look « webtoon » moderne. Z-Image : plutôt Ghibli. Wan s202 : cheveux bruns (dérive). |
| 3 BD | **Z-Image**, Klein | Les deux produisent une vraie case avec bordure et un vrai trait de ligne claire. Mains et tasse correctes. Juggernaut : plus illustratif. |
| 4 3D | **Klein**, Z-Image | Rendu de film d'animation crédible, peau et cheveux bien matiérés. Wan s202 : objet bleu parasite sur l'épaule. Juggernaut : à mi-chemin, peu convaincant. |
| 5 peinture | Juggernaut, Z-Image | Juggernaut montre de vraies touches de pinceau. Z-Image est plus doux. Klein dérive vers l'anime. Wan : personnage trop petit dans le cadre. |
| 6 semi-réaliste | Klein, Z-Image | Peu de différence avec l'anime ou la peinture selon le modèle : style mal défini, peu utile. |
| 7 cinéma | **Z-Image**, Klein | Z-Image : le plus crédible du test, avec grain pellicule, mains naturelles et décor cohérent. Klein très proche. Juggernaut : visage plus « IA », sujet petit. Wan s202 : main déformée. |
| 8 photo | **Klein** | Klein : naturel, mains correctes (5 doigts, prise de la tasse juste). Z-Image prend « taken with a DSLR » au pied de la lettre et pose un appareil photo sur la table : reformuler le prompt. Juggernaut : bon mais glossy, tient la tasse d'une main, texture pavée sur la table. |

## Bilan provisoire (avant revue visuelle de l'utilisateur)
- **Retenus pour la suite : Z-Image Turbo et FLUX.2 Klein 4B.** Ce sont les seuls à suivre le style demandé sur toute l'échelle, avec mains et visages propres. Klein est ~1,8× plus rapide (92 contre 163 s) ; Z-Image est un cran au-dessus en cinéma et en BD.
- **Wan 5B T2I écarté pour l'image fixe** : le plus lent (161 s), sans être meilleur sur aucun style (dérives sur s202, sujet petit). Il reste retenu pour l'I2V.
- **Animagine** : à garder seulement pour l'anime pur, où il reste le meilleur et le moins cher en RAM.
- **Juggernaut** : seul vrai gain en peinture. Ailleurs, il est dominé par Klein, plus rapide en régime de qualité égale ou meilleure. À trancher après la revue.
- Les styles qui rendent le mieux sur cette machine : cinéma/photo, BD ligne claire et 3D. Flat et semi-réaliste sont les moins convaincants.
- Shortlist : `shortlist/00_overview.jpg` + 14 images numérotées.

## Revue visuelle de l'utilisateur (2026-10-29)
Galerie : artefact « Échelle de styles » (`gallery/`). 16 favoris retenus :
`klein_1_flat_s202, zimage_1_flat_s101, animagine_2_anime_s101, klein_2_anime_s202, zimage_2_anime_s101, zimage_2_anime_s202, klein_3_bd_s202, zimage_3_bd_s202, zimage_4_3d_s101, zimage_4_3d_s202, animagine_5_paint_s202, zimage_5_paint_s202, zimage_7_cine_s101, zimage_7_cine_s202, klein_8_photo_s101, zimage_8_photo_s202`

| Modèle | Favoris | Styles couverts |
|---|---|---|
| **Z-Image Turbo** | **10** | flat, anime, BD, 3D, peinture, cinéma, photo |
| FLUX.2 Klein 4B | 4 | flat, anime, BD, photo |
| Animagine XL 4.0 | 2 | anime, peinture |
| Juggernaut XL v9 | 0 | — |
| Wan 5B T2I | 0 | — |

- **Z-Image Turbo retenu comme modèle principal** : seul modèle choisi dans les 7 styles gardés, avec les deux seeds en anime, 3D et cinéma (consistance). Contrairement à mon tri, il passe devant Klein en 3D.
- Klein reste un second choix (~1,8× plus rapide). Animagine est gardé pour l'anime et la peinture anime.
- **Juggernaut écarté** (0 favori, même en peinture et en photo) ; Wan T2I confirmé écarté. Checkpoint supprimé le 2026-10-29 (7,1 Go), sorties gardées dans `out/juggernaut/`.
- Critère décisif de l'utilisateur : **le nombre de doigts**. Beaucoup de mes recommandations ont été écartées pour des mains fausses que mon tri, fait sur vignettes et sur des crops tête-mains, n'avait pas vues. Recontrôle sur des crops des mains (`sheets/hands_missed_*.jpg`) : mains douteuses (doigts fusionnés ou en trop, mains en moufle) surtout chez Klein (cinéma s101, 3D s202, BD s101, flat s101), plus Animagine anime s202 et Z-Image flat s202. À cette résolution, je ne peux pas compter les doigts de façon sûre partout. Le contrôle des mains doit devenir une étape à part entière du tri.
- Animagine : l'utilisateur aime beaucoup son rendu, même hors thème. Il n'est derrière que parce qu'il ne suit pas le style demandé.
- Style semi-réaliste abandonné : aucun favori.
- Le défaut « appareil photo sur la table » de Z-Image en photo n'a pas gêné à la revue (`zimage_8_photo_s202` retenu) ; à corriger quand même dans le prompt.
- Prochaine cible : la vitesse de Z-Image (163 s/image, dont seulement ~32 s de sampling).

## Z-Image : décodage groupé + prompt photo corrigé (2026-10-29)
Machine libre (aucun autre modèle en cache), ComfyUI relancé, `--lowvram --disable-pinned-memory`. Jobs de 2 seeds (101, 202).
- Mode actuel : chaque seed est samplée puis décodée tout de suite, et le VAE décharge le GGUF entre deux seeds.
- Mode groupé (`group_decode` dans `gen.py`) : les seeds sont samplées l'une après l'autre, puis `LatentBatch` → un seul `VAEDecode` → un seul `SaveImage`.

| Job | Mode | Temps/image |
|---|---|---|
| 9_photo2 (1er job, chargement) | groupé | 90 s |
| 4_3d | actuel | 108 s |
| 7_cine | actuel | 109 s |
| 4_3d | groupé | 93 s |
| 7_cine | groupé | 90 s |

- **Gain du décodage groupé : −16 %** (108,5 → 91,5 s/image), à conditions égales.
- **Images identiques au bit près** : groupé = actuel = originaux du 25/10, sur les 4 images comparées. Aucun coût en qualité.
- **Retenu : c'est le mode par défaut de `gen.py`** (`--per-seed-decode` pour l'ancien comportement).
- L'écart avec les 163 s du 25/10 vient surtout de l'état de la machine. Ce jour-là, le cache de Wan et de Klein occupait la RAM (6 Go de swap) ; aujourd'hui, 1 à 3 Go. Le mode actuel passe déjà à 108 s sur machine libre. À retenir : enchaîner plusieurs modèles dans une même session ComfyUI ralentit nettement Z-Image.
- Décomposition d'un job groupé de 172 s : ~61 s de sampling (2 × 8 steps à 3,5–4,1 s), 24 s d'initialisation du GGUF (une seule fois au lieu d'une par seed), le reste en chargement/encodage Qwen3 (5,4 Go) et en décodage. Ces frais fixes sont payés une fois par job : **mettre plus de seeds par job** devrait faire tendre le coût vers ~30–35 s/image. C'est la prochaine mesure à faire (4 et 8 seeds par job).
- Prompt photo, voir plus bas.

## Z-Image : nombre de seeds par job (2026-10-30)
Même session ComfyUI, décodage groupé, style `7_cine`, même prompt pour tous les jobs : l'encodage texte est en cache, comme pour une série d'images sur un même prompt.
- 1er essai invalide (seeds 101…808 réutilisées) : ComfyUI met en cache la sortie de chaque KSampler à entrées identiques, donc les seeds déjà calculées au job précédent n'étaient pas refaites (4 seeds : 31 s/image, 8 seeds : 22 s/image, faux). **Pour tout banc ComfyUI, utiliser des seeds neuves à chaque job.**
- Banc valide, seeds neuves à chaque job :

| Seeds par job | Job | Par image |
|---|---|---|
| 2 (1001-1002) | 122 s | 61 s |
| 4 (2001-2004) | 188 s | 47 s |
| 8 (3001-3008) | 319 s | **40 s** |

- Modèle linéaire qui colle aux 3 points : **job ≈ 56 s de frais fixes + 33 s par image**, plus ~66 s si le prompt est nouveau (encodage Qwen3, mesuré : même job à 2 seeds en 188 s sans cache contre 122 s avec).
- En pratique : 8 images sur un nouveau prompt ≈ (56 + 66 + 8 × 33) / 8 ≈ **48 s/image**, contre 163 s/image le 25/10. **Gain ×3,4** en cumulant décodage groupé, machine libre et 8 seeds par job.
- Le lot de 8 en un seul décodage VAE passe sans OOM (VRAM max 4,8 Go).
- Constat qualité : Z-Image varie très peu d'une seed à l'autre (même personnage, même cadrage, même ambiance sur les 14 images, `sheets/cine_seeds.jpg`). Atout pour la consistance d'une série ; pour varier, il faut jouer sur le prompt, pas sur la seed. Les mains de ces 14 images restent à valider par l'utilisateur (ajoutées à la galerie).
- **Recommandation : générer par lots de 8 seeds par prompt** quand on cherche la bonne image.
- Revue de l'utilisateur (2026-10-30) : **mains correctes sur les 14 images**, qualité jugée excellente. Seule incohérence : un vélo à l'arrière-plan tient debout tout seul, sans béquille ni support. Jugé pas encore gênant. Piste si besoin : préciser « bicycles leaning against a rack » dans `SUBJECT`.

## Prompt photo corrigé (2026-10-29)
- Prompt photo : `9_photo2` (« Natural-light portrait photograph, shallow depth of field… ») remplace la mention « DSLR and an 85mm lens ». **Plus d'appareil photo sur la table** (2/2 seeds). Mains plausibles au zoom (`sheets/photo2_check.jpg`), à confirmer par l'utilisateur. `8_photo` est gardé dans `STYLES` pour la traçabilité.
