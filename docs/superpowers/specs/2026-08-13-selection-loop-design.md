# Interactive Selection Loop Design

**Date:** 2026-08-13

## Goal

Replace the index-number prompt + `y/N` confirmation in `depscleaner` with an interactive toggle loop, so users can select all folders or select/deselect individual ones without retyping the full list.

## Current Behavior

`prompt_deletion` in `depscleaner/cleaner.py` asks for space-separated indices, then asks a separate `y/N` confirmation before deleting. The `--yes`/`-y` flag skips that confirmation but still requires typing indices.

## New Behavior

After found folders and sizes are printed, an interactive loop runs. The loop itself is the confirmation — deletion happens immediately on `done`.

```
[0] Found: /a/node_modules, Size: 1.00 KiB
[1] Found: /a/vendor, Size: 2.00 KiB
[2] Found: /b/node_modules, Size: 3.00 KiB

Selected: none
Command (numbers to toggle, 'all', 'none', 'done', 'quit'): all
Selected: 0 1 2
Command (numbers to toggle, 'all', 'none', 'done', 'quit'): 1
Selected: 0 2
Command (numbers to toggle, 'all', 'none', 'done', 'quit'): done
Deleted /a/node_modules
Deleted /b/node_modules
Total space freed: 4.00 KiB
```

### Commands

| Input                     | Effect                                             |
| ------------------------- | -------------------------------------------------- |
| Space-separated numbers   | Toggle each listed index on/off                    |
| `all`                     | Select every found folder                          |
| `none`                    | Clear the selection                                |
| `done` (or empty enter)   | Delete the current selection                       |
| `quit` / `q`              | Abort, delete nothing                              |

### Edge Cases

- Out-of-range numbers are ignored, with a note printed.
- Unparseable input re-prompts, showing the list of valid commands.
- `done` with an empty selection prints "No folders selected — nothing to delete." and returns.
- Empty `found_folders` prints "No dependency folders found." and returns before the loop (unchanged).
- `--dry-run` short-circuits before the loop (unchanged).

## Changes

### `depscleaner/cleaner.py`

- Replace `_ask_for_indices` with `_select_indices`: a loop maintaining a `set` of selected indices, printing `Selected: <indices>` after each command.
- `prompt_deletion` calls `_select_indices`, then deletes the returned selection directly. The `y/N` confirm block is removed.
- Remove `self.yes` and the `dry_run`/`yes` constructor handling for `yes` (constructor signature becomes `(path='.', depth=DEFAULT_DEPTH, dry_run=False)`).

### `depscleaner/cleaner.py` — `build_parser`

- Remove the `-y, --yes` argument.

### `depscleaner/__main__.py`

- Stop passing `yes` to `DepsCleaner`.

### `README.md`

- Remove the `-y, --yes` row from the options table.

### Tests (`tests/test_cleaner.py`)

- Rewrite `test_run_yes_deletes_selected` and `test_run_retries_on_invalid_indices` to drive the loop via `monkeypatch` on `builtins.input`.
- Replace `test_run_aborts_without_confirmation` with a `quit`-abort test.
- Update `test_build_parser_defaults` / `test_build_parser_parses_flags` to drop `yes`.
- Add new tests:
  - toggle a number on then off with a second entry
  - `all` then deselect one
  - `none` clears the selection
  - `done` with nothing selected deletes nothing
  - invalid input re-prompts and still completes
  - out-of-range indices are ignored

## Non-Goals

- No persistent selection state across runs.
- No multi-select via arrow keys / curses.
- `--dry-run` behavior is unchanged.
