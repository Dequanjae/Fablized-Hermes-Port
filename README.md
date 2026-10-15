# Fablized Hermes Port

Hermes-native adaptation of [fivetaku/fablize](https://github.com/fivetaku/fablize). Adds task routing, evidence tracking, and a bounded verification gate using Hermes plugin hooks.

## What it does

- `pre_llm_call`: classifies task depth and injects the matching investigation or render-verification pack.
- `post_tool_call`: records file changes, verification results, and repeated failures.
- `pre_verify`: asks Hermes to continue when a deep task changed files but has no observed successful verification. Hermes bounds continuation attempts.
- No tool overrides, external dependencies, or credentials required.

The `pre_verify` gate runs only after code edits. Hermes does not expose a generic hook that blocks every final response, so this port cannot enforce the original promise-without-action guard on no-edit turns.

## Install

From this repository root:

```bash
mkdir -p ~/.hermes/extensions/fablize ~/.hermes/plugins ~/.hermes/skills/fablize
cp -a extension/fablize/. ~/.hermes/extensions/fablize/
cp -a plugin/fablize ~/.hermes/plugins/
cp skill/fablize/SKILL.md ~/.hermes/skills/fablize/SKILL.md
hermes config get skills.auto_load
# Merge "fablize" into the existing list; preserve other loaded skills.
hermes config set skills.auto_load '["existing-skill", "fablize"]'
hermes plugins validate ~/.hermes/plugins/fablize
hermes plugins enable fablize --no-allow-tool-override
hermes plugins doctor fablize
```

The plugin defaults to `~/.hermes/extensions/fablize`. Set `FABLIZE_ROOT` if you install the support files elsewhere.

## Verify

Run the focused callback checks:

```bash
python -m unittest discover -s tests -v
```

Then test with a deep task that edits code: without a successful verification result, the gate should request one before completion.

## Notes

This repository contains the Hermes adapter and only the upstream files it needs. The upstream Fablize project remains the source for its packs and ledger logic. MIT license and attribution retained from upstream.
