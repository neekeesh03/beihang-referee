# State and provenance

Each run is a state machine. Stages write immutable-ish artifacts to the run directory and checkpoint the current `ReviewState`. Inputs receive SHA-256 hashes. The final run manifest hashes the serialized state, records the review purpose and depth, and preserves the exact input manifest.

Important artifacts include `document_map.json`, `package_audit.json`, `review_plan.json`, `reporting_audit.json`, `reproducibility_report.json`, `reviewer_disagreement.json`, concern-admission logs, `provenance_report.json`, `evidence_graph.dot`, `review.json`, `review.md`, `review.html`, `major_concerns.csv`, and `run_manifest.json`.

A provenance score is diagnostic, not a truth score. It asks whether a criticism points to resolvable anchors with document IDs, locators, quoted facts, and confidence metadata. Semantic validity is still assessed by the independent verifier.
