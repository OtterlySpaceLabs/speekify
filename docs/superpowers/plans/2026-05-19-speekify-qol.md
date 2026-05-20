# Speekify QoL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Speekify permissive by default through automatic cleanup, fallback batching, and clearer completion feedback.

**Architecture:** The permissive synthesis pipeline lives in `src/speekify/tts.py` and returns structured synthesis metadata to the TUI. The app keeps UI orchestration and displays a concise success summary built from that metadata.

**Tech Stack:** Python 3.14 runtime, Textual, Supertonic SDK, numpy, pytest, ruff.

---

### Task 1: Lock the Desired Behavior with Tests

**Files:**
- Modify: `tests/test_tts.py`
- Modify: `tests/test_app_logging.py`
- Modify: `tests/test_config.py`

- [ ] Add failing tests for permissive removal of unsupported characters.
- [ ] Add failing tests for external batching and merged synthesis results.
- [ ] Add failing tests for the user-visible success summary in the TUI.
- [ ] Update the step-range expectations to match the actual SDK.

### Task 2: Implement Permissive Preparation and External Batching

**Files:**
- Modify: `src/speekify/tts.py`

- [ ] Add structured preparation and synthesis result dataclasses.
- [ ] Reuse Supertonic preprocessing when available.
- [ ] Remove unsupported characters automatically and keep a summary.
- [ ] Split oversized prepared text into external batches and merge into one final waveform.

### Task 3: Integrate the New Flow into the TUI

**Files:**
- Modify: `src/speekify/app.py`
- Modify: `src/speekify/config.py`

- [ ] Update the UI flow to prepare text, synthesize externally-batched audio, and save the merged waveform.
- [ ] Show success details for output path, duration, auto-cleanup, and batch count.
- [ ] Align the step validation range with the actual SDK limits.

### Task 4: Refresh Docs and Verify

**Files:**
- Modify: `README.md`

- [ ] Document permissive cleanup and auto-batching.
- [ ] Run pytest and ruff and fix any issues.
