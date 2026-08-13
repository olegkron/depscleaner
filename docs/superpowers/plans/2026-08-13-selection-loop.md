# Interactive Selection Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the index-number prompt + `y/N` confirm in `depscleaner` with an interactive toggle loop (commands: numbers to toggle, `all`, `none`, `done`, `quit`), and remove the now-redundant `--yes` flag.

**Architecture:** Rework `prompt_deletion` in `depscleaner/cleaner.py` to drive a new `_select_indices` method that keeps a `set` of selected indices across loop iterations, printing the current selection after each command. The loop is itself the confirmation — `done` deletes immediately. `--yes`/`-y` is removed from the parser, `__main__`, constructor, README, and tests.

**Tech Stack:** Python stdlib, pytest (in `.venv`).

---

## Task 1: Interactive toggle loop

**Files:**
- Modify: `depscleaner/cleaner.py:20-25` (constructor), `70-94` (prompt_deletion), `96-114` (_ask_for_indices → _select_indices)
- Test: `tests/test_cleaner.py:119-155`

**Spec ref:** "Replace `_ask_for_indices` with `_select_indices`", "`prompt_deletion` deletes directly after `done`", "Remove `self.yes` and the `yes` constructor parameter".

- [ ] **Step 1: Rewrite the run-flow tests**

In `tests/test_cleaner.py`, replace everything from `def test_run_does_not_prompt_when_nothing_found` (line 119) through `def test_run_dry_run_deletes_nothing` (line 155) with:

```python
def patch_input(monkeypatch, inputs):
    it = iter(inputs)
    monkeypatch.setattr('builtins.input', lambda _: next(it))


def test_run_does_not_prompt_when_nothing_found(tmp_path, monkeypatch):
    monkeypatch.setattr('builtins.input', lambda _: pytest.fail('must not prompt'))
    DepsCleaner(path=str(tmp_path)).run()


def test_run_toggle_loop_deletes_selected(tmp_path, monkeypatch, capsys):
    root = sample_project(tmp_path)
    patch_input(monkeypatch, ['0', 'done'])
    DepsCleaner(path=str(root)).run()
    assert not (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()
    assert 'Total space freed' in capsys.readouterr().out


def test_run_toggle_number_twice_deselects(tmp_path, monkeypatch):
    root = sample_project(tmp_path)
    patch_input(monkeypatch, ['0', '0', 'done'])
    DepsCleaner(path=str(root)).run()
    assert (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()


def test_run_all_then_deselect_one(tmp_path, monkeypatch):
    root = sample_project(tmp_path)
    patch_input(monkeypatch, ['all', '0', 'done'])
    DepsCleaner(path=str(root)).run()
    assert (root / 'app' / 'node_modules').exists()
    assert not (root / 'app' / 'vendor').exists()


def test_run_none_clears_selection(tmp_path, monkeypatch):
    root = sample_project(tmp_path)
    patch_input(monkeypatch, ['all', 'none', 'done'])
    DepsCleaner(path=str(root)).run()
    assert (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()


def test_run_done_with_empty_selection_deletes_nothing(tmp_path, monkeypatch, capsys):
    root = sample_project(tmp_path)
    patch_input(monkeypatch, [''])
    DepsCleaner(path=str(root)).run()
    assert (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()
    assert 'No folders selected' in capsys.readouterr().out


def test_run_quit_aborts(tmp_path, monkeypatch):
    root = sample_project(tmp_path)
    patch_input(monkeypatch, ['0', 'quit'])
    DepsCleaner(path=str(root)).run()
    assert (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()


def test_run_invalid_input_reprompts(tmp_path, monkeypatch, capsys):
    root = sample_project(tmp_path)
    patch_input(monkeypatch, ['banana', '0', 'done'])
    DepsCleaner(path=str(root)).run()
    assert not (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()
    assert 'Ignoring invalid inputs' in capsys.readouterr().out


def test_run_out_of_range_indices_ignored(tmp_path, monkeypatch, capsys):
    root = sample_project(tmp_path)
    patch_input(monkeypatch, ['99', '0', 'done'])
    DepsCleaner(path=str(root)).run()
    assert not (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()
    assert 'Ignoring out-of-range indices' in capsys.readouterr().out


def test_run_dry_run_deletes_nothing(tmp_path, capsys):
    root = sample_project(tmp_path)
    DepsCleaner(path=str(root), dry_run=True).run()
    assert (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()
    assert 'Dry run' in capsys.readouterr().out
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_cleaner.py::test_run_toggle_loop_deletes_selected tests/test_cleaner.py::test_run_all_then_deselect_one tests/test_cleaner.py::test_run_invalid_input_reprompts tests/test_cleaner.py::test_run_out_of_range_indices_ignored -q`
Expected: these 4 fail (old code aborts on the `'done'` confirm, leaving folders undeleted). Note: `test_run_toggle_number_twice_deselects` and `test_run_quit_aborts` may already pass against old code — that is fine; they are regression tests for the new semantics.

- [ ] **Step 3: Replace the constructor**

In `depscleaner/cleaner.py`, replace lines 20-25:

```python
    def __init__(self, path='.', depth=DEFAULT_DEPTH, dry_run=False, yes=False):
        self.path = path
        self.depth = depth
        self.dry_run = dry_run
        self.yes = yes
        self.found_folders = []
```

with:

```python
    def __init__(self, path='.', depth=DEFAULT_DEPTH, dry_run=False):
        self.path = path
        self.depth = depth
        self.dry_run = dry_run
        self.found_folders = []
```

- [ ] **Step 4: Replace `prompt_deletion`**

Replace lines 70-94:

```python
    def prompt_deletion(self):
        if not self.found_folders:
            print("No dependency folders found.")
            return

        indices = self._select_indices()
        if indices is None:
            return
        if not indices:
            print("No folders selected — nothing to delete.")
            return

        total_deleted_size = 0
        for i in indices:
            folder = self.found_folders[i]
            try:
                self.delete_folder(folder['path'])
                print(f"Deleted {folder['path']}")
                total_deleted_size += folder['size']
            except OSError as e:
                logger.error("Error deleting %s: %s", folder['path'], e)

        print(f"Total space freed: {get_human_readable_size(total_deleted_size)}")
```

- [ ] **Step 5: Replace `_ask_for_indices` with `_select_indices`**

Replace lines 96-114:

```python
    def _select_indices(self):
        total = len(self.found_folders)
        selected = set()
        while True:
            display = ' '.join(str(i) for i in sorted(selected)) if selected else 'none'
            print(f"Selected: {display}")
            raw = input("Command (numbers to toggle, 'all', 'none', 'done', 'quit'): ").strip().lower()
            if raw in ('', 'done'):
                return sorted(selected)
            if raw in ('quit', 'q'):
                print("Aborted.")
                return None
            if raw == 'all':
                selected = set(range(total))
                continue
            if raw == 'none':
                selected = set()
                continue
            parts = raw.split()
            indices = []
            invalid = []
            for part in parts:
                try:
                    indices.append(int(part))
                except ValueError:
                    invalid.append(part)
            if invalid:
                print(f"Ignoring invalid inputs: {invalid}")
            out_of_range = [i for i in indices if not (0 <= i < total)]
            if out_of_range:
                print(f"Ignoring out-of-range indices: {out_of_range}")
            for i in indices:
                if 0 <= i < total:
                    if i in selected:
                        selected.discard(i)
                    else:
                        selected.add(i)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_cleaner.py -q`
Expected: all pass (including the 2 that were green before — they still validate the new behavior).

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: interactive toggle loop for folder selection"
```

---

## Task 2: Remove the `--yes` flag

**Files:**
- Modify: `depscleaner/cleaner.py:130-131` (build_parser)
- Modify: `depscleaner/__main__.py` (DepsCleaner construction)
- Test: `tests/test_cleaner.py:91-108` (parser tests)

**Spec ref:** "Remove the `-y, --yes` argument", "`__main__.py` stop passing `yes`".

- [ ] **Step 1: Update the parser tests**

In `tests/test_cleaner.py`, replace lines 91-108 with:

```python
def test_build_parser_defaults():
    from depscleaner.cleaner import build_parser

    args = build_parser().parse_args([])
    assert args.path == '.'
    assert args.depth == DepsCleaner.DEFAULT_DEPTH
    assert args.dry_run is False


def test_build_parser_parses_flags():
    from depscleaner.cleaner import build_parser

    args = build_parser().parse_args(['/tmp/foo', '--depth', '5', '--dry-run'])
    assert args.path == '/tmp/foo'
    assert args.depth == 5
    assert args.dry_run is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_cleaner.py::test_build_parser_defaults -q`
Expected: FAIL with `AttributeError: 'Namespace' object has no attribute 'yes'` (old parser still sets `yes`; new test no longer reads it — the assertion fails because `args.yes` no longer exists after Step 3, or the flag still exists before Step 3; either way this test should be run AFTER Step 3 for the intended red). If run before Step 3 it passes — run it again after Step 3 to confirm it fails, then proceed.

- [ ] **Step 3: Remove the flag from `build_parser`**

In `depscleaner/cleaner.py`, replace lines 128-131:

```python
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be deleted without deleting anything')
    parser.add_argument('-y', '--yes', action='store_true',
                        help='Skip the interactive confirmation prompt')
```

with:

```python
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be deleted without deleting anything')
```

- [ ] **Step 4: Update `__main__.py`**

In `depscleaner/__main__.py`, replace:

```python
    cleaner = DepsCleaner(path=args.path, depth=args.depth, dry_run=args.dry_run, yes=args.yes)
```

with:

```python
    cleaner = DepsCleaner(path=args.path, depth=args.depth, dry_run=args.dry_run)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_cleaner.py -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: remove now-redundant --yes flag"
```

---

## Task 3: Docs, full verification, reinstall

**Files:**
- Modify: `README.md`
- (no test changes)

- [ ] **Step 1: Update the README options table**

In `README.md`, remove this row from the options table:

```markdown
| `-y, --yes`  | Skip the interactive confirmation prompt                |
```

- [ ] **Step 2: Full suite + CLI smoke test**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m depscleaner --help
```

Expected: all tests pass; help lists `path`, `--depth`, `--dry-run`, `--version` (no `--yes`).

- [ ] **Step 3: Manual interactive smoke test**

```bash
tmp=$(mktemp -d) && mkdir -p "$tmp/a/node_modules" "$tmp/a/vendor" "$tmp/b/node_modules"
printf 'all\n1\ndone\n' | .venv/bin/python -m depscleaner "$tmp"
ls "$tmp/a" "$tmp/b"
```

Expected: prints `Selected: none`, then `Selected: 0 1 2`, then `Selected: 0 2` after deselecting `1`, then deletes `a/node_modules` and `b/node_modules`; `vendor` remains.

- [ ] **Step 4: Reinstall the system-wide CLI**

```bash
pipx install --force .
```

Run from the repo root. Expected: `installed package depscleaner 1.0.0`.

- [ ] **Step 5: Verify system-wide command from another directory**

```bash
cd /tmp && depscleaner --version
```

Expected: `depscleaner 1.0.0`.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "docs: remove --yes from usage table"
```

---

## Self-Review Notes

- **Spec coverage:** toggle loop (Task 1), `done`/empty → delete, `quit`/`q` → abort, `all`/`none`, out-of-range noted, invalid input re-prompts, empty-selection message (Task 1), `--yes` removed from parser/`__main__`/constructor/README/tests (Tasks 1-3), all new tests from the spec (Task 1).
- **Type consistency:** `_select_indices` returns `sorted(selected)` (list of ints) or `None`; `prompt_deletion` handles `None` (abort) and `[]` (nothing selected). Constructor is `(path, depth, dry_run)` everywhere — no caller passes `yes` after Task 2.
- **Known non-red tests:** `test_run_toggle_number_twice_deselects` and `test_run_quit_aborts` pass against old code; they exist to lock in the new semantics and are still meaningful.
