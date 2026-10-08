# Examples

The `examples/` directory contains a deterministic public demo designed to run without an API key or network access.

## Offline Core Review Pipeline demo

```bash
referee review examples/demo_manuscript.md \
  --pipeline core \
  --mode standard \
  --provider scripted \
  --scripted-responses examples/demo_responses.json \
  --search-backend none \
  --run-id demo
```

Files:

- `demo_manuscript.md` — deliberately simple pre/post observational manuscript with an overclaimed causal conclusion.
- `demo_responses.json` — deterministic Core Review Pipeline model responses used by the scripted provider.
- `expected_demo_review.md` — reference final review produced by the current demo fixture.

The public demo is covered by a source regression test. If the Core contract changes, update the fixture and expected output in the same change.
