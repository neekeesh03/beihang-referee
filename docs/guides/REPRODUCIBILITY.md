# Reproducibility auditing

The package scanner inventories data files, hashes them, locates environment and lock files, counts source-code lines, detects seed-setting signals, flags hard-coded absolute paths and network calls, and inspects notebooks for execution order, outputs, and possible embedded secrets.

These checks establish reproducibility evidence and risks; they are not equivalent to successfully rerunning an analysis. Executing third-party research code requires a future isolated sandbox and an explicit trust policy.
