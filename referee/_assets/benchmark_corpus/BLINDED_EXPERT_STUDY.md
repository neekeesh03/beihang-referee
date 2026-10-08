# Blinded expert validation protocol

Use `referee.evals.prepare_blinded_study` to mix Referee, human-reviewer and baseline-system concerns without source labels. Experts rate each atomic concern on 1–5 scales for factual correctness, evidence grounding, scientific importance, severity appropriateness, actionability, non-redundancy and usefulness, plus a yes/no `include_in_review` judgment. Keep the source codebook separate until ratings are locked. Report inter-rater reliability and source-level comparisons with uncertainty intervals.
