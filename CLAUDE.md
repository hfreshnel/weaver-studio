# CLAUDE.md

## Objectif du dossier
Tester des IA, principalement de la **génération d'image et de vidéo**. Chaque test/modèle vit dans son propre sous-dossier.

## Philosophie du projet
Au-delà du test de modèles, le but réel est de trouver le **meilleur compromis pour automatiser la génération de médias de haute qualité sur un PC comme celui-ci**.
- Pas de limite au nombre de modèles/outils dans une pipeline, tant que le résultat est bon.
- **Chaque étape de la pipeline doit être justifiée** par un gain mesuré (qualité, consistance, vitesse).
- Si un outil simple donne un résultat égal, meilleur ou plus consistant (ou moins coûteux), le préférer à un modèle lourd ; toujours en tenir compte.
- Tester et comparer autant que nécessaire (mêmes entrées, mêmes critères), puis ne garder dans la boucle que le chemin qui mène au meilleur résultat.
- Priorité : qualité du résultat. Ensuite seulement, optimiser la consommation de ressources (temps, VRAM/RAM, puissance de calcul).
- Consigner chaque comparaison et sa conclusion (retenu / écarté, et pourquoi) dans le `NOTES.md` concerné.

## Langue
Répondre en français. Code, noms de fichiers et commits en anglais.

## Machine (modeste : à prendre en compte pour tout choix de modèle)
- WSL2 (Linux 6.6) sous Windows, shell zsh
- CPU : Intel Core i7-11800H (8 cœurs / 16 threads)
- RAM : ~14 Go visibles dans WSL
- GPU : NVIDIA GeForce RTX 3060 Laptop, **6 Go de VRAM** (driver Windows 592.82, CUDA 13.1, `nvidia-smi` fonctionne dans WSL)
- Privilégier : modèles légers/quantifiés (fp16, fp8, GGUF Q4/Q5, int4), faible résolution, peu de frames, offload CPU, attention slicing / VAE tiling
- Éviter : modèles qui exigent >6 Go de VRAM sans variante quantifiée ou offload, téléchargements de plusieurs dizaines de Go sans prévenir
- Repères : SD 1.5 / SDXL (avec optimisations) / Flux quantifié en GGUF passent ; pour la vidéo, viser des modèles légers (ex. LTX-Video, Wan 1.3B/2.2 5B quantifiés) en basse résolution et peu de frames

## Conventions de travail
- Un sous-dossier par outil/modèle testé, avec son propre environnement Python isolé (venv ou uv), jamais d'install globale.
- Les poids de modèles, sorties (images/vidéos) et venv ne vont pas dans git : ajouter au `.gitignore`.
- Noter dans un `NOTES.md` par sous-dossier : modèle + version, commande lancée, temps de génération, VRAM/RAM utilisée, verdict qualité.
- Avant de télécharger un gros modèle (>2 Go) ou d'installer des dépendances lourdes (torch, CUDA), annoncer la taille et demander confirmation.
- Garder les scripts de test courts et reproductibles (seed fixée, prompt en argument).
- Ne pas lancer de génération longue en avant-plan : utiliser l'exécution en arrière-plan et rapporter le temps.

## Git
Ce dossier racine n'est pas (encore) un dépôt git ; chaque projet peut avoir le sien. Ne committer que sur demande.
