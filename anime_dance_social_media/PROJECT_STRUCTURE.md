# Project Structure & Workflow Analysis

This document outlines the professional modular architecture of the Anime Dance & Remix Pipeline.

## 🏗️ Core Architecture

The project is organized into four main layers:

### 1. `workflows/` (Orchestration Layer)
**Runnable scripts that define end-to-end pipelines.**
*   **`main_pipeline.py`**: (Run via `python -m workflows.main_pipeline`)
    *   **Role**: **The Chief Orchestrator**. Takes a source video -> Generates Outfit Variants -> Animates them -> Remixes Video -> Calls Audio Scoring.
*   **`character_gen.py`**:
    *   **Role**: Asset Factory. Generates characters + cosplay variants using Gemini and updates `character_db.json`.
*   **`audio_pipeline.py`**:
    *   **Role**: Sonic Brain. Analyzes video BPM/Structure -> Generates Structured Phonk (Minimax) -> Syncs Audio.
*   **`watermark_job.py`**:
    *   **Role**: Branding/Post-Process. Generates & applies transparent mascot stickers.

### 2. `core/` (Business Logic Layer)
**Reusable functional components.**
*   **`animation.py`**:
    *   **Role**: Handles Kling AI interactions, frame extraction, and video generation logic.
*   **`cosplay.py`**:
    *   **Role**: Specialized logic for Photo-Realism Style Transfer (Img2Img editing).

### 3. `services/` (Infrastructure Layer)
**Pure API wrappers.**
*   **`gemini_service.py`**:
    *   **Role**: Centralized Google Gemini Client (Text, Image, Video Analysis, Rotation Keys).
*   **`minimax_service.py`**:
    *   **Role**: Centralized Minimax Client (Music Generation).

### 4. `utils/` (Support Layer)
**General purpose utilities.**
*   **`download.py`**: Helper to download videos/files.
*   **`cleanup.py`**: Helper to remove unwanted frames/temp files.
*   **`batch_utils.py`**: Tools for batch processing folder operations.
*   **`tests/`**: Verification scripts (e.g., `test_imports.py`).

---

## 📂 Data Directories
*   **`output/`**: Centralized output folder.
    *   **`characters/`**: Stores generated character images and `character_db.json`.
    *   **`dances/`**: Raw Kling Generation & Cosplay Dances.
    *   **`remixes/`**: Final results from `main_pipeline` (Remixed Videos).
    *   **`temp/`**: Temporary working directory.

---

## 🗑️ History (Refactored)
*   *Old: `run_outfit_remix.py`* → **`workflows/main_pipeline.py`**
*   *Old: `generate_characters.py`* → **`workflows/character_gen.py`**
*   *Old: `run_advanced_scoring.py`* → **`workflows/audio_pipeline.py`**
*   *Old: `ai_service` folder* → **`services/`**
