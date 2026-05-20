# Speekify QoL Design

**Goal**

Make Speekify permissive by default so generation succeeds in the largest possible number of real-world cases.

**Approved Direction**

- Automatically normalize and reformat text before synthesis.
- Automatically remove unsupported characters instead of blocking immediately.
- Automatically split oversized inputs into external batches and merge them into one final WAV.
- Show the user a short post-run summary of what the app corrected.
- Only fail when the cleaned text is still unusable or when model / I/O failures occur.

**Architecture**

- Keep the TUI focused on orchestration and display.
- Move permissive text preparation and external batch synthesis into `src/speekify/tts.py`.
- Reuse Supertonic's own preprocessing and internal chunking where possible, then complement it with external batching only when the full input would exceed the SDK's total length limit.

**Behavior**

- Input text is preprocessed with Supertonic's Unicode processor when available.
- Unsupported characters are removed automatically, counted, and reported back to the user.
- If the prepared text exceeds Supertonic's total text limit, the app splits it into batches on paragraph/sentence boundaries, falling back to hard splits when necessary.
- All batches are synthesized and merged into one final WAV with configured silence between external batches.
- Success output includes path, duration, batch count, and cleanup summary.
