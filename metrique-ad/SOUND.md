# MÉTRIQUE launch ad — sound cue sheet (v1 is silent)

Music: minimal afro-house, 108–112 BPM, royalty-free (Pixabay / YouTube Audio Library), no identifiable voice.
Cut the edit on the beat grid: at 110 BPM one beat = 0.545 s; the picture cuts sit on a 0.5 s grid, so nudge cuts by ±1–2 frames when laying the track.

| Time | Picture | Sound |
|---|---|---|
| 0:00 | P01 pipe bursts | No music. Dry, close water-burst SFX (hook carried by real sound). |
| 0:02 | P02 thumb scrolls | Fast scroll ticks, phone haptic buzz. |
| 0:03–0:12 | Problem (P03–P05) | Low muffled bass drone, subtle clock tick, unanswered ringback tone at 0:03.5. |
| 0:11.6 | Navy wipe | Rising whoosh (0.4 s) ending in a soft low impact at 0:12.0. |
| 0:12 | Logo reveal | Beat drops in (kick + shaker), short gold "shimmer" on the gold line (avoid cliché sparkle). |
| 0:15–0:22 | H1 + sectors | Groove continues; typewriter-free soft key taps on each H1 word; pop on each sector chip (19.0, 19.45, 19.9, 20.35, 20.8). |
| 0:22–0:40 | Demo steps 1-2-3 | Build: add percussion layer per step. UI click on each tap ripple (22.7, 23.8, 27.3). "Pop" on each step badge (22.0, 28.0, 34.0). Swish on the gold wipes (27.75, 33.75). Gentle 2-note chime when the escrow line appears (38.6). |
| 0:40 | P08 arrival | Full groove. |
| 0:43–0:46 | P09 leak stops | Drop music for half a bar when the leak stops (~0:44.5): single water drop SFX, then music back. |
| 0:46–0:52 | Confirm + street | Groove + warm pad, light street ambience (motorbikes) under P11. |
| 0:51.6 | Fade to white | Reverse cymbal into the final card. |
| 0:52–0:60 | Final card | Final chord at 0:54.6 (logo), hold, clean cut at 0:59.5. |

Mix: music −16 LUFS integrated for social, SFX ducked under nothing (no voice-over). Export AAC 192 kb/s 48 kHz, then mux:
`ffmpeg -i out/metrique_launch_v1.mp4 -i mix.wav -c:v copy -c:a aac -b:a 192k -ar 48000 -shortest out/metrique_launch_v1_audio.mp4`
