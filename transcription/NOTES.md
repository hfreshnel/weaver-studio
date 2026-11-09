# Transcription audio

## Setup
- Outil : faster-whisper 1.2.1 (ctranslate2 4.8.3), modèle `large-v3-turbo` (~1.6 Go, cache HF)
- venv : `.venv/` (Python 3.14), cuBLAS 12 + cuDNN 9 via pip (`nvidia-cublas-cu12`, `nvidia-cudnn-cu12`)
- `run.sh` ajoute les libs CUDA pip au `LD_LIBRARY_PATH` puis lance `transcribe.py`
- Décodage audio via `ffmpeg` système : le PyAV tiré par faster-whisper est incompatible
  (`TypeError: open() got an unexpected keyword argument 'metadata_errors'`)

## Commande
```
./run.sh "../22 oct. à 09-20.m4a"            # --lang fr --model large-v3-turbo --compute-type int8_float16
```
Sorties dans `outputs/` : `.txt` (brut), `.timestamps.txt`, `.srt`.

## Run 2026-10-22 — m4a 25 min 42 s, FR, GPU int8_float16, beam 5, VAD
- Chargement modèle : 13.5 s (le 1er run a pris 85 s, téléchargement compris)
- Transcription : **56 s**, soit environ 27x le temps réel ; 71 s au total
- VRAM pic : ~1.25 Go / 6 Go ; RAM pic : ~2.1 Go
- Qualité : très bonne sur le français parlé, ponctuation correcte. Points faibles : noms propres
  et sigles mal orthographiés (écoles, entreprises), à relire. Pas de diarisation (locuteurs non séparés).
- Verdict : **retenu**. Rapide, léger, largement dans les limites de la machine.

## Run 2026-10-25 — mp4 1 h 05 min 29 s (vidéo, réunion à plusieurs), FR, GPU int8_float16, beam 5, VAD
Mêmes entrées, deux réglages comparés :

| | défaut (`condition_on_previous_text=True`) | `--no-condition` |
|---|---|---|
| Transcription | 241 s (~16x temps réel) | **164 s (~24x)** |
| Total (wall) | 4 min 11 s | **3 min 10 s** |
| Segments | 2 496 | 1 165 |
| Mots/segment après 10 min | 2.3 à 5.2 | **4.6 à 8.2** |
| Lignes dupliquées les plus fréquentes | ~30 (`ok`, `Euh...`) | ~8 |

- VRAM pic : ~1.5 Go ; RAM pic : ~4.2 Go (la vidéo entière décodée en mémoire)
- Défaut : à partir de ~10 min le modèle dérive (il se conditionne sur sa propre sortie dégradée) :
  plus de ponctuation ni de majuscules, texte haché en 2-3 mots par ligne, doublons. Difficile à lire.
- `--no-condition` : la dérive disparaît, phrases complètes. Restent des fragments courts sur les
  échanges rapides et superposés (limite sans diarisation). ~7 % de mots en moins, surtout des doublons supprimés.
- Verdict : **`--no-condition` retenu pour les enregistrements longs** (> ~20 min). Le défaut
  reste correct sur le m4a de 25 min.

```
./run.sh "2026-10-25 15-18-21.mp4" --no-condition --out outputs/nocond
```

## Pistes si besoin
- Séparer les locuteurs : whisperX ou pyannote (demande torch, plus lourd) ; à tester seulement si nécessaire.
- Noms propres : passer `initial_prompt` avec le vocabulaire attendu.

## Run 2026-10-27 — m4a 1 h 12 min (entretien, FR avec passages en anglais), GPU int8_float16, beam 5, VAD, `--no-condition`
- Chargement modèle : 14.1 s ; total (wall) : **3 min 28 s** (~21x temps réel)
- RAM pic : ~4.8 Go (audio entier décodé en mémoire)
- Sortie : ~6 960 mots, `outputs/nocond/27 oct. à 13-01.*`
- Qualité : phrases complètes, pas de dérive. Mélange FR/EN : le modèle force `fr`, donc les passages
  anglais sont parfois déformés ; noms propres et termes techniques mal orthographiés (ex. « Simulatio »,
  « CKAMI System », « ACG Lake »). Pas de diarisation.
- Piste : relancer avec `initial_prompt` (vocabulaire attendu) ou `--lang` auto si les passages anglais comptent.

### Relance 2026-10-27 en anglais (`--lang en --no-condition`, sortie `outputs/nocond-en/`)
- Total 3 min 05 s, RAM pic ~4.5 Go. Le run `--lang fr` ci-dessus était une erreur : l'échange est en anglais.
- Verdict : **`--lang en` retenu** pour cet audio (texte nettement plus fidèle). Rester vigilant sur les noms propres
  (« Sikami System », « ACG Lake », « Simulatio »). Leçon : vérifier la langue avant de lancer (le défaut est `fr`).
