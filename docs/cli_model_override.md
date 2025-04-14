# CLI --model Override Behavior

## Overview

The `--model` CLI argument allows users to specify the model for a single session. This setting takes the highest priority for the duration of the session but does not persist to disk or configuration files.

## Precedence

- If `--model` is provided, it is stored in the in-memory `runtime_config` and takes precedence over local/global config files.
- All model accesses (including in the chat shell and agent instantiation) reference `unified_config.get('model')`, which checks `runtime_config` first.
- The override lasts only for the current process/session.

## Usage

```bash
python -m janito --model openrouter/other-model "Your prompt here"
```

Or in chat shell mode:

```bash
python -m janito --model openrouter/other-model
```

## Technical Details

- The CLI parser accepts `--model`.
- On startup, if `--model` is provided, it sets `runtime_config['model']`.
- All code paths use `unified_config.get('model')` for model selection.

## Why?

This ensures that temporary model overrides are possible without affecting persistent configuration, and that all components (including the chat shell) use the same model for the session.
