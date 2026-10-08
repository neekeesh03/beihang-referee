# Security model

Manuscripts are untrusted data. Embedded instructions never override system or runtime policy. The package includes prompt-injection signaling, secret detection/redaction helpers, safe output-path checks, input hashing, bounded network behavior, and disabled execution of untrusted manuscript code by default.

Reproducibility scanning reads source code and notebooks as data. It does not execute them unless a future sandboxed execution subsystem is explicitly enabled.
