"""Shot list: prompts, negatives, models and frame counts (see plan storyboard)."""

CLIENT = ("a Beninese woman in her early thirties, dark skin, short natural coily hair, "
          "mustard-yellow and navy wax-print blouse, small gold stud earrings")
PLUMBER = ("a Beninese man in his forties, short trimmed beard, "
           "navy blue work coverall over a grey t-shirt")
SET = ("modest modern apartment in Cotonou, beige walls, white tiled kitchen, "
       "daylight from a side window")

NEG_WAN = ("text, letters, watermark, logo, subtitles, readable screen, UI, deformed hands, "
           "extra fingers, fused fingers, distorted face, morphing face, identity change, "
           "extra limbs, blurry, low quality, jpeg artifacts, overexposed, static frame, flicker, "
           "cartoon, anime, 3d render, neon, cyberpunk, robot")
NEG_LTX = ("worst quality, inconsistent motion, blurry, jittery, distorted, text, watermark, "
           "deformed hands, morphing")

SHOTS = {
    "P01": dict(model="wan", frames=49, seed=1001, prompt=(
        "Extreme close-up under a kitchen sink, a corroded metal pipe joint suddenly bursts, a jet of "
        "water sprays toward the camera, droplets sparkling in cold side light, a hand rushes into frame "
        "trying to block the leak, shallow depth of field, handheld camera with slight shake, cinematic, "
        "desaturated cool tones, photorealistic")),
    "P02": dict(model="ltx", frames=25, seed=1002, prompt=(
        "Close-up of a thumb scrolling quickly on a smartphone held in one hand, the screen is a soft "
        "out-of-focus glow, dim kitchen background, cool bluish light on the fingers, hesitant movement, "
        "shallow depth of field, photorealistic, cinematic")),
    "P03": dict(model="wan", frames=73, seed=1003, prompt=(
        f"Medium shot, {CLIENT}, standing in a {SET}, phone pressed to her ear, worried expression, "
        "looking down at water pooling on the tiled floor, she sighs and shifts her weight, static camera "
        "with a very slow push-in, cool overcast daylight, desaturated, cinematic 35mm, photorealistic")),
    "P04": dict(model="wan", frames=73, seed=1004, prompt=(
        "Close-up of two dark-skinned West African hands at the doorway of a house in Cotonou, one hand "
        "gives a folded stack of colorful West African CFA franc banknotes to the other hand, both people "
        "in casual clothes, faces out of frame, the banknotes slightly out of focus, slow deliberate motion, "
        "cool muted light, shallow depth of field, photorealistic"), neg_extra=", US dollars, green banknotes, suit, white skin"),
    "P05": dict(model="wan", frames=73, seed=1005, prompt=(
        "An open grey metal electrical breaker box mounted on a beige wall, its door left wide open, loose "
        "red, blue and yellow wires dangling out of it, half-finished repair, an abandoned open toolbox on "
        "the tiled floor below, nobody in the room, daylight slowly dimming, very slow dolly-in, melancholic, "
        "desaturated cool tones, photorealistic")),
    "P06": dict(model="wan", frames=49, seed=1006, prompt=(
        f"Over-the-shoulder shot of {CLIENT} sitting on a sofa, her thumb taps on her smartphone, screen "
        "blurred and unreadable, a hint of relief, warm window light, shallow depth of field, photorealistic")),
    "P07": dict(model="wan", frames=49, seed=1007, prompt=(
        f"Medium close-up of {PLUMBER} in a workshop, his phone vibrates, he looks at the screen "
        "(unreadable) and gives a confident nod, warm light, slight handheld, photorealistic")),
    "P08": dict(model="wan", frames=73, seed=1008, prompt=(
        f"At a metal gate of a Cotonou house in warm late-afternoon light, {PLUMBER} carrying a toolbox "
        f"arrives and greets {CLIENT} with a polite handshake, camera slowly tracks from behind her "
        "shoulder, golden hour, warm tones, cinematic, photorealistic")),
    "P09": dict(model="wan", frames=73, seed=1009, prompt=(
        "Close-up of a plumber's hands tightening a new chrome pipe fitting under a kitchen sink with an "
        "adjustable wrench, the leak stops, a final drop of water falls, clean warm light, slow push-in, "
        "shallow depth of field, photorealistic")),
    "P10": dict(model="wan", frames=73, seed=1010, prompt=(
        f"Medium shot of {CLIENT} in her bright kitchen, relieved smile, she looks at her phone and taps "
        "the screen to confirm (screen unreadable), dry tiled floor, warm golden light, slow push-in, "
        "photorealistic, cinematic")),
    "P11": dict(model="wan", frames=73, seed=1011, prompt=(
        "Wide shot of a lively street in Cotonou at golden hour, zemidjan motorbikes passing slowly, "
        "people walking, warm orange sunlight, slow aerial-like crane up, cinematic, photorealistic, "
        "no text on signs")),
}
