# Evidence-lock contract

The system does not treat fluent criticism as sufficient evidence. Major comments are admitted only when the structured concern contains all required fields and every anchor identifier exists in the run's evidence store. Red-team and steelman stages may revise concerns, but the deterministic gate is authoritative.

After admission, an independent verifier attempts to falsify the criticism. In deep and exhaustive modes it may request a bounded targeted evidence chase. If the concern remains under-evidenced after the configured chase, it fails closed and cannot remain major or critical.

This design is intended to reduce three common LLM-review failures: invented manuscript facts, disproportionate criticism, and moving closure targets.
