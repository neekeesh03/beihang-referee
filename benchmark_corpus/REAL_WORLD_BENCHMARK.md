# Real-paper benchmark protocol

Referee intentionally does not redistribute third-party manuscripts or reviewer reports in this repository. Use `schemas/real_world_benchmark.schema.json` to create a legally shareable/local benchmark from public papers or submissions and multiple human reviews.

Gold labels are **atomic adjudicated concerns**, not accept/reject decisions. Each concern records location, severity, expert agreement, alternative interpretations, and an acceptable closure. Keep gold data out of model prompts. Run Referee on the manuscript alone, then score its admitted concerns against the adjudicated set.

Recommended first study: 100–300 papers stratified across domains, at least two independent expert annotators per paper plus adjudication, and a held-out test split. Report concern precision/recall, severity macro-F1, grounding, calibration, inter-rater reliability, cost, latency, and per-domain performance.
