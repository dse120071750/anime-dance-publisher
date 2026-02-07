# Character Dance Remix Workflow

This document outlines the end-to-end automated workflow for generating consistent character dance remix videos with AI-composed music.

## Overview
The pipeline transforms a source dance video into a multi-outfit remix, maintaining the subject's identity while swapping styles and surroundings, finally scoring it with beat-synced custom Phonk music.

---

## 1. Vision & Asset Generation
- **Base Frame Extraction**: The system extracts the first frame of the input video to serve as the identity and pose reference.
- **Outfit Variant Generation (Gemini Image 3)**:
    - Uses "Jennie Kim" (Blackpink) and "Gentle Monster" (Futuristic Art) as stylistic foundations.
    - Generates high-fashion variants (e.g., *Jennie Swimsuit*, *Jennie K-Pop Techwear*).
    - **Identity Consistency**: Enforces strict reference to the original face, hair, and body type.
- **Motion Transfer (Kling AI)**:
    - Submits the new outfit images and the original dance video to Kling.
    - Kling transfers the exact motion/choreography from the source video onto the newly generated character assets.

## 2. Video Editing & Transitions
- **Segmented Remixing**:
    - The final video is split into three equal parts:
        1. **0 - 33%**: Original Video.
        2. **33 - 66%**: Jennie Swimsuit Variant.
        3. **66 - 100%**: Jennie K-Pop/Techwear Variant.
- **Zoom Slam (Shake) Transitions**:
    - At each cut point, a "Zoom Slam" effect is applied.
    - The camera rapidly scales (1.1x -> 1.0x) to simulate a high-energy transition impact.

## 3. Advanced Audio Scoring (Structured Sync)
This phase ensures the music matches the energy of the dance.
- **Visual Structural Analysis**:
    - **Gemini 3 Flash** analyzes the dance video to identify specific sections (Intro, Build, Drop, Verse).
    - It detects the **Visual BPM** and the exact timestamp of the **First Hard Hit** (Dance Drop).
- **Structured Music Generation (Minimax Music 2.5)**:
    - A custom Phonk track is request from Minimax using the detected BPM and the section breakdown.
    - Explicit section tags (`[Chorus]`, `[Drop]`) are used to ensure the music follows the choreography's ebb and flow.
- **Intelligent Synchronization**:
    - Analyzes the *generated audio* to find the musical drop.
    - Calculates the **Offset** between the Video Drop and Audio Drop.
    - Trims or delays the audio to ensure the "Beat Drop" aligns perfectly with the "Dance Drop" to the millisecond.

---

## Technical Stack
- **AI Models**: Gemini 3 Flash (Analysis/Vision), Gemini Image 3 (Image Gen), Kling AI (Video Gen), Minimax 2.5 (Music).
- **Libraries**: MoviePy v2.2.1 (Editing), Cloud Vision/GenAI (Analysis).
- **Stylistic DNA**: High-Fashion K-Pop, futuristic cyberpunk aesthetics.

---

## Final Output Files
- `REMIX_JENNIE_[Source].mp4`: The edited video without music.
- `REMIX_JENNIE_[Source]_structured_scored.mp4`: The final beat-synced masterpiece.
