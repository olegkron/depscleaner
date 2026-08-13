# Depscleaner Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the bugs and structural problems in the `depscleaner` CLI so it is crash-safe on bad input, safe against symlink traversal, correctly packaged, properly logged, and covered by tests.

**Architecture:** Restructure the repo into a real Python package (`depscleaner/`) so `find_packages()` and the console entry point actually work, then replace the hand-rolled CLI/size/delete/logging code with standard-library equivalents (`argparse`, `shutil.rmtree`, `logging`), and drive every change with pytest TDD. Keep the same public behavior: `depscleaner [path] [--depth N]`.

**Tech Stack:** Python 3.6+, stdlib (`argparse`, `logging`, `shutil`, `os.scandir`), pytest for tests, `setup.py` for packaging.

---

## Pre-flight

The repo currently has uncommitted work (`git status` shows `M depscleaner.py` and untracked `__init__.py`, `.serena/`). Before starting Task 1:

```bash
git add -A && git commit -m "chore: snapshot current state before hardening"
```

Expected: `nothing to commit, working tree clean` on the following `git status`.

## File Structure (after this plan)

```
.
├── conftest.py                     # empty; makes `depscleaner` importable by pytest
├── requirements-dev.txt            # pytest
├── setup.py                        # now actually finds the package
├── README.md                       # updated usage/flags
├── depscleaner/                    # the real package
│   ├── __init__.py                 # __version__
│   ├── __main__.py                 # entry point: argparse + logging setup + run
│   ├── cleaner.py                  # DepsCleaner class + build_parser()
│   ├── utils.py                    # calculate_directory_size, get_human_readable_size
│   └── validator.py                # validate_directory, validate_depth
└── tests/
    ├── test_cleaner.py
    ├── test_utils.py
    └── test_validator.py
```

`logger.py` is deleted — replaced by stdlib `logging`. `depscleaner.py` is renamed to `cleaner.py` (a package and module sharing the name `depscleaner` is confusing).

---

### Task 1: Restructure into a proper package

**Files:**
- Create: `depscleaner/__init__.py`
- Create: `depscleaner/__main__.py`
- Create: `depscleaner/cleaner.py`
- Create: `depscleaner/utils.py`
- Create: `depscleaner/validator.py`
- Modify: `setup.py`
- Delete: `depscleaner.py`, `__main__.py`, `__init__.py`, `utils.py`, `validator.py` (repo root copies)

**Context:** `find_packages()` currently returns nothing (verified: `depscleaner.egg-info/SOURCES.txt` is empty), so `pip install` installs a broken package whose console script points at a non-existent `depscleaner` module. Fix by giving the repo a real `depscleaner/` package directory.

- [ ] **Step 1: Move the source files into a package directory**

```bash
mkdir depscleaner
mv __init__.py depscleaner/__init__.py
mv __main__.py depscleaner/__main__.py
mv depscleaner.py depscleaner/cleaner.py
mv utils.py depscleaner/utils.py
mv validator.py depscleaner/validator.py
```

Do NOT move `logger.py` yet — it gets deleted in Task 8. Expected: `ls depscleaner/` shows `__init__.py  __main__.py  cleaner.py  utils.py  validator.py`.

- [ ] **Step 2: Update the `__main__.py` import**

In `depscleaner/__main__.py`, change line 4 from:

```python
from .depscleaner import DepsCleaner
```

to:

```python
from .cleaner import DepsCleaner
```

- [ ] **Step 3: Set the package version**

Replace the whole content of `depscleaner/__init__.py` with:

```python
__version__ = '1.0.0'
```

- [ ] **Step 4: Update `setup.py`**

Keep `setup.py` as-is except confirm it is exactly:

```python
from setuptools import setup, find_packages

setup(
    name='depscleaner',
    version='1.0.0',
    author='Oleg Kron',
    description='A tool to clean up dependency folders in projects',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'depscleaner=depscleaner.__main__:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
```

No change needed to the code itself — the restructure makes `find_packages()` return `['depscleaner']`.

- [ ] **Step 5: Verify the package imports**

Run: `python3 -c "import depscleaner; from depscleaner.cleaner import DepsCleaner; from depscleaner import __version__; print(__version__)"`
Expected: `1.0.0` with no ImportError.

- [ ] **Step 6: Verify the console script wiring**

Run: `python3 -m depscleaner --help`
Expected: the module is a package now, so `python -m depscleaner` executes `depscleaner/__main__.py` (which still prints the old "Error:" style if anything fails, or nothing if it runs — the arg parsing is fixed in Task 6; a non-zero exit here is fine, an `ImportError` is not).

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "refactor: restructure into a proper depscleaner package"
```

---

### Task 2: Test infrastructure

**Files:**
- Create: `conftest.py` (repo root, empty)
- Create: `requirements-dev.txt`
- Create: `tests/test_utils.py` (placeholder to verify pytest wiring)

- [ ] **Step 1: Create the dev requirements file**

```bash
mkdir -p tests
```

Create `requirements-dev.txt`:

```
pytest
```

- [ ] **Step 2: Install the package editable + pytest**

```bash
python3 -m pip install -e . pytest
```

If the build fails with a setuptools/pip error on Python 3.14, retry with `python3 -m pip install -e . --no-build-isolation pytest`.
Expected: `Successfully installed depscleaner-1.0.0 pytest-...`.

- [ ] **Step 3: Create root conftest.py**

Create `conftest.py` at the repo root with only a comment (it makes pytest insert the repo root on `sys.path`, so `import depscleaner` works even without the editable install):

```python
# Ensures the repo root is on sys.path so `import depscleaner` works under pytest.
```

- [ ] **Step 4: Sanity-check pytest wiring**

Create `tests/test_utils.py`:

```python
def test_pytest_wiring():
    from depscleaner.utils import calculate_directory_size
    assert calculate_directory_size is not None
```

Run: `python3 -m pytest tests/test_utils.py -q`
Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "test: add pytest test infrastructure"
```

---

### Task 3: Fix `utils.py` (size + human-readable)

**Files:**
- Modify: `depscleaner/utils.py`
- Test: `tests/test_utils.py`

**Fixes:** `calculate_directory_size` races (`os.path.exists` + `os.path.getsize`) and follows directory symlinks (double-counting + escape). `get_human_readable_size` uses 1024 but labels bytes as KB/MB (should be KiB/MiB).

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_utils.py` entirely:

```python
from depscleaner.utils import calculate_directory_size, get_human_readable_size


def test_pytest_wiring():
    assert calculate_directory_size is not None


def test_size_zero():
    assert get_human_readable_size(0) == '0.00 B'


def test_size_exact_kib():
    assert get_human_readable_size(1024) == '1.00 KiB'


def test_size_fraction_kib():
    assert get_human_readable_size(1536) == '1.50 KiB'


def test_size_round_trips():
    assert get_human_readable_size(1) == '1.00 B'


def test_calculate_directory_size_recurses(tmp_path):
    (tmp_path / 'a.txt').write_text('x' * 100)
    sub = tmp_path / 'sub'
    sub.mkdir()
    (sub / 'b.txt').write_text('y' * 200)
    assert calculate_directory_size(str(tmp_path)) == 300


def test_calculate_directory_size_ignores_symlinked_dir(tmp_path):
    real = tmp_path / 'real'
    real.mkdir()
    (real / 'f.txt').write_text('x' * 500)
    link = tmp_path / 'link'
    link.symlink_to(real, target_is_directory=True)
    assert calculate_directory_size(str(tmp_path)) == 500
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_utils.py -q`
Expected: failures — `test_size_exact_kib` fails (label is `KB` not `KiB`), `test_calculate_directory_size_ignores_symlinked_dir` fails (size is 1000, symlink followed).

- [ ] **Step 3: Replace the implementation**

Replace the whole content of `depscleaner/utils.py`:

```python
import os


def calculate_directory_size(path):
    total = 0
    with os.scandir(path) as entries:
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    total += calculate_directory_size(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
            except OSError:
                continue
    return total


def get_human_readable_size(size, precision=2):
    suffixes = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
    suffix_index = 0
    while size > 1024 and suffix_index < len(suffixes) - 1:
        suffix_index += 1
        size /= 1024
    return f"{size:.{precision}f} {suffixes[suffix_index]}"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_utils.py -q`
Expected: `7 passed`.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "fix: make size calculation symlink-safe and size labels accurate"
```

---

### Task 4: Fix `find_folders` (matching, depth, symlinks)

**Files:**
- Modify: `depscleaner/cleaner.py`
- Test: `tests/test_cleaner.py`

**Fixes:** `re.match` matches prefixes (`node_modules_old`); depth is tracked by two redundant counters; `entry.is_dir()` follows symlinks (can descend into a symlinked tree); `index = len(self.found_folders) - 1` is dead code.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cleaner.py`:

```python
import pytest

from depscleaner.cleaner import DepsCleaner


def sample_project(root):
    app = root / 'app'
    app.mkdir()
    (app / 'node_modules').mkdir()
    (app / 'vendor').mkdir()
    (app / 'src').mkdir()
    (app / 'node_modules' / 'x').mkdir()
    pkg = root / 'pkg'
    pkg.mkdir()
    (pkg / 'node_modules_old').mkdir()
    return root


def test_is_dependency_folder_exact_match_only():
    cleaner = DepsCleaner()
    assert cleaner.is_dependency_folder('node_modules')
    assert cleaner.is_dependency_folder('vendor')
    assert not cleaner.is_dependency_folder('node_modules_old')
    assert not cleaner.is_dependency_folder('src')


def test_find_folders_discovers_dependencies(tmp_path):
    root = sample_project(tmp_path)
    cleaner = DepsCleaner(path=str(root))
    cleaner.find_folders(cleaner.path, cleaner.depth)
    paths = {folder['path'] for folder in cleaner.found_folders}
    assert paths == {
        str(root / 'app' / 'node_modules'),
        str(root / 'app' / 'vendor'),
    }


def test_find_folders_does_not_descend_into_matched(tmp_path):
    root = sample_project(tmp_path)
    cleaner = DepsCleaner(path=str(root))
    cleaner.find_folders(cleaner.path, cleaner.depth)
    assert len(cleaner.found_folders) == 2


def test_find_folders_respects_depth(tmp_path):
    root = sample_project(tmp_path)
    (root / 'a' / 'b' / 'c' / 'node_modules').mkdir(parents=True)
    cleaner = DepsCleaner(path=str(root), depth=2)
    cleaner.find_folders(cleaner.path, cleaner.depth)
    paths = {folder['path'] for folder in cleaner.found_folders}
    assert str(root / 'a' / 'b' / 'c' / 'node_modules') not in paths


def test_find_folders_does_not_follow_symlinks(tmp_path):
    target = tmp_path / 'target'
    target.mkdir()
    (target / 'node_modules').mkdir()
    link = tmp_path / 'link'
    link.symlink_to(target, target_is_directory=True)
    cleaner = DepsCleaner(path=str(tmp_path))
    cleaner.find_folders(cleaner.path, cleaner.depth)
    assert len(cleaner.found_folders) == 1
    assert cleaner.found_folders[0]['path'] == str(target / 'node_modules')


def test_cleaner_default_depth_is_three():
    assert DepsCleaner.DEFAULT_DEPTH == 3
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_cleaner.py -q`
Expected: `test_find_folders_discovers_dependencies` fails — `pkg/node_modules_old` is currently matched by `re.match`.

- [ ] **Step 3: Replace the scanning methods**

Replace the `find_folders` method in `depscleaner/cleaner.py` (current lines 34-52) with:

```python
    def find_folders(self, path, depth):
        if depth == 0:
            return
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    if self.is_dependency_folder(entry.name):
                        self.add_found_folder(entry.path)
                    else:
                        self.find_folders(entry.path, depth - 1)
        except OSError as e:
            logger.warning("Error scanning directory %s: %s", path, e)

    def is_dependency_folder(self, name):
        return any(re.fullmatch(pattern, name) for pattern in self.DEPENDENCY_FOLDERS_REGEX)

    def add_found_folder(self, path):
        size = calculate_directory_size(path)
        self.found_folders.append({'path': path, 'size': size})
        index = len(self.found_folders) - 1
        print(f"[{index}] Found: {path}, Size: {get_human_readable_size(size)}")
```

Update the imports at the top of `depscleaner/cleaner.py` (currently lines 3-7) to:

```python
import logging
import os
import re

from .utils import calculate_directory_size, get_human_readable_size
from .validator import validate_directory, validate_depth

logger = logging.getLogger(__name__)
```

**Note:** `logger` is referenced now but logging is only wired up in Task 8. In the meantime Python's `lastResort` handler prints WARNING+ to stderr, so nothing is lost.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_cleaner.py -q`
Expected: `7 passed`.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "fix: exact dependency matching, single depth counter, skip symlinks when scanning"
```

---

### Task 5: Delete via `shutil.rmtree`

**Files:**
- Modify: `depscleaner/cleaner.py`
- Test: `tests/test_cleaner.py`

**Fix:** the hand-rolled `recursive_delete` follows symlinked dirs (deletes the symlink target's real files) and half-deletes on permission errors. `shutil.rmtree` is the standard, safe tool.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_cleaner.py`:

```python
def test_delete_folder_removes_tree(tmp_path):
    dep = tmp_path / 'deps'
    (dep / 'a' / 'b').mkdir(parents=True)
    (dep / 'a' / 'f.txt').write_text('x')
    DepsCleaner().delete_folder(str(dep))
    assert not dep.exists()


def test_delete_folder_does_not_follow_symlinks(tmp_path):
    dep = tmp_path / 'deps'
    dep.mkdir()
    real = tmp_path / 'real'
    real.mkdir()
    (real / 'keep.txt').write_text('keep')
    (dep / 'link').symlink_to(real, target_is_directory=True)
    DepsCleaner().delete_folder(str(dep))
    assert not dep.exists()
    assert real.exists()
    assert (real / 'keep.txt').exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_cleaner.py::test_delete_folder_does_not_follow_symlinks -q`
Expected: FAIL — the old `recursive_delete` follows `link` into `real` and deletes `keep.txt`.

- [ ] **Step 3: Replace `recursive_delete`**

Replace the `recursive_delete` method (current lines 71-77) with:

```python
    def delete_folder(self, path):
        shutil.rmtree(path)
```

Add `import shutil` to the imports in `depscleaner/cleaner.py` (next to `import re`).

- [ ] **Step 4: Update the one caller**

In `prompt_deletion` (current line 63) change `self.recursive_delete(folder['path'])` to `self.delete_folder(folder['path'])`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_cleaner.py -q`
Expected: `9 passed`.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "fix: use shutil.rmtree for safe, symlink-safe deletion"
```

---

### Task 6: CLI via `argparse`

**Files:**
- Modify: `depscleaner/cleaner.py`
- Modify: `depscleaner/__main__.py`
- Test: `tests/test_cleaner.py`

**Fixes:** `sys.argv` poking crashes with `ValueError` on a non-numeric `--depth` before validation runs; no `--help`/`--version`/`--dry-run`/`--yes`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cleaner.py`:

```python
def test_build_parser_defaults():
    from depscleaner.cleaner import build_parser

    args = build_parser().parse_args([])
    assert args.path == '.'
    assert args.depth == DepsCleaner.DEFAULT_DEPTH
    assert args.dry_run is False
    assert args.yes is False


def test_build_parser_parses_flags():
    from depscleaner.cleaner import build_parser

    args = build_parser().parse_args(['/tmp/foo', '--depth', '5', '--dry-run', '--yes'])
    assert args.path == '/tmp/foo'
    assert args.depth == 5
    assert args.dry_run is True
    assert args.yes is True


def test_version_flag(capsys):
    from depscleaner.cleaner import build_parser

    with pytest.raises(SystemExit):
        build_parser().parse_args(['--version'])
    assert 'depscleaner' in capsys.readouterr().out
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_cleaner.py::test_build_parser_defaults -q`
Expected: FAIL with `ImportError` — `build_parser` doesn't exist yet.

- [ ] **Step 3: Add `build_parser` and rewrite the constructor**

Add to `depscleaner/cleaner.py`, directly after the class:

```python
def build_parser():
    parser = argparse.ArgumentParser(
        prog='depscleaner',
        description='Find and remove dependency folders like node_modules.',
    )
    parser.add_argument('path', nargs='?', default='.', help='Root directory to scan (default: current directory)')
    parser.add_argument('--depth', type=int, default=DepsCleaner.DEFAULT_DEPTH,
                        help='Maximum nesting depth to scan (default: %(default)s)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be deleted without deleting anything')
    parser.add_argument('-y', '--yes', action='store_true',
                        help='Skip the interactive confirmation prompt')
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {__version__}')
    return parser
```

Add `import argparse` to the imports in `depscleaner/cleaner.py` and change the `from .utils import ...` import to also pull the version:

```python
import argparse
import logging
import os
import re
import shutil

from . import __version__
from .utils import calculate_directory_size, get_human_readable_size
from .validator import validate_directory, validate_depth

logger = logging.getLogger(__name__)
```

Replace the constructor (current lines 14-17) with:

```python
    def __init__(self, path='.', depth=DEFAULT_DEPTH, dry_run=False, yes=False):
        self.path = path
        self.depth = depth
        self.dry_run = dry_run
        self.yes = yes
        self.found_folders = []
```

- [ ] **Step 4: Update `depscleaner/__main__.py`**

Replace the whole file:

```python
from .cleaner import DepsCleaner, build_parser


def main():
    args = build_parser().parse_args()
    cleaner = DepsCleaner(path=args.path, depth=args.depth, dry_run=args.dry_run, yes=args.yes)
    cleaner.run()


if __name__ == '__main__':
    main()
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_cleaner.py -q`
Expected: `12 passed`.

- [ ] **Step 6: Smoke-test `--help` and `--version`**

```bash
python3 -m depscleaner --help
python3 -m depscleaner --version
```

Expected: help text lists `path`, `--depth`, `--dry-run`, `-y/--yes`, `--version`; version prints `depscleaner 1.0.0`.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: replace manual argv parsing with argparse"
```

---

### Task 7: Robust interactive deletion

**Files:**
- Modify: `depscleaner/cleaner.py`
- Test: `tests/test_cleaner.py`

**Fixes:** `int()` crashes on non-numeric input; no confirmation of what is deleted; prompts even when nothing was found.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cleaner.py`:

```python
def test_run_does_not_prompt_when_nothing_found(tmp_path, monkeypatch):
    monkeypatch.setattr('builtins.input', lambda _: pytest.fail('must not prompt'))
    DepsCleaner(path=str(tmp_path)).run()


def test_run_yes_deletes_selected(tmp_path, monkeypatch, capsys):
    root = sample_project(tmp_path)
    monkeypatch.setattr('builtins.input', lambda _: '0')
    DepsCleaner(path=str(root), yes=True).run()
    assert not (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()
    assert 'Total space freed' in capsys.readouterr().out


def test_run_retries_on_invalid_indices(tmp_path, monkeypatch):
    root = sample_project(tmp_path)
    inputs = iter(['abc', '0 1'])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    DepsCleaner(path=str(root), yes=True).run()
    assert not (root / 'app' / 'node_modules').exists()
    assert not (root / 'app' / 'vendor').exists()


def test_run_aborts_without_confirmation(tmp_path, monkeypatch):
    root = sample_project(tmp_path)
    inputs = iter(['0', 'n'])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    DepsCleaner(path=str(root)).run()
    assert (root / 'app' / 'node_modules').exists()


def test_run_dry_run_deletes_nothing(tmp_path, capsys):
    root = sample_project(tmp_path)
    DepsCleaner(path=str(root), dry_run=True).run()
    assert (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()
    assert 'Dry run' in capsys.readouterr().out


def test_run_rejects_invalid_path(tmp_path, capsys):
    DepsCleaner(path=str(tmp_path / 'missing')).run()
    captured = capsys.readouterr()
    assert 'Invalid directory path' in captured.out + captured.err


def test_run_rejects_negative_depth(tmp_path, capsys):
    DepsCleaner(path=str(tmp_path), depth=-1).run()
    captured = capsys.readouterr()
    assert 'Invalid depth value' in captured.out + captured.err
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_cleaner.py -q`
Expected: several failures, notably `test_run_retries_on_invalid_indices` (crash on `int('abc')`) and `test_run_does_not_prompt_when_nothing_found` (currently calls `input()`).

- [ ] **Step 3: Replace `run`, `prompt_deletion` and add `_ask_for_indices`**

Replace the `run` method (current lines 19-32) with:

```python
    def run(self):
        if not validate_directory(self.path):
            logger.error('Invalid directory path: %s', self.path)
            return

        if not validate_depth(self.depth):
            logger.error('Invalid depth value: %s', self.depth)
            return

        self.find_folders(self.path, self.depth)
        total_size = sum(folder['size'] for folder in self.found_folders)
        print(f"Total potential space to be freed: {get_human_readable_size(total_size)}")

        if self.dry_run:
            print(f"Dry run — {len(self.found_folders)} folder(s) would be deleted, nothing removed.")
            return

        self.prompt_deletion()
```

Replace the `prompt_deletion` method (current lines 54-69) with:

```python
    def prompt_deletion(self):
        if not self.found_folders:
            print("No dependency folders found.")
            return

        indices = self._ask_for_indices()

        if not self.yes:
            paths = '\n'.join(f"[{i}] {self.found_folders[i]['path']}" for i in indices)
            confirm = input(f"Delete these {len(indices)} folder(s)?\n{paths}\n[y/N] ").strip().lower()
            if confirm not in ('y', 'yes'):
                print("Aborted.")
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

    def _ask_for_indices(self):
        total = len(self.found_folders)
        while True:
            raw = input("Enter the indices of folders to delete (separated by space): ").strip()
            if not raw:
                print("No indices entered.")
                continue
            try:
                indices = [int(part) for part in raw.split()]
            except ValueError:
                print("Invalid input — enter space-separated numbers.")
                continue
            valid = sorted(set(i for i in indices if 0 <= i < total))
            invalid = sorted(set(i for i in indices if not (0 <= i < total)))
            if invalid:
                print(f"Ignoring out-of-range indices: {invalid}")
            if not valid:
                continue
            return valid
```

- [ ] **Step 4: Remove the dead `__main__` block in `cleaner.py`**

Delete the trailing block in `depscleaner/cleaner.py`:

```python
if __name__ == "__main__":
    import sys
    cleaner = DepsCleaner(sys.argv[1:])
    cleaner.run()
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest -q`
Expected: all tests pass (`test_utils` + `test_validator` + `test_cleaner`).

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: add confirmation prompt, input validation, and dry-run mode"
```

---

### Task 8: Replace `logger.py` with stdlib `logging`

**Files:**
- Modify: `depscleaner/__main__.py`
- Delete: `depscleaner/logger.py`
- Test: `tests/test_cleaner.py` (existing error-path tests cover the change)

**Fix:** `logger.py` prints *and* appends to `error.log` in the CWD — so running the tool pollutes whatever directory you scan with a new file, and has no timestamps.

- [ ] **Step 1: Delete the old logger module**

```bash
git rm depscleaner/logger.py
```

Run: `python3 -m pytest -q`
Expected: all tests still pass (nothing imports `logger` anymore).

- [ ] **Step 2: Add logging setup to `__main__.py`**

Replace the whole `depscleaner/__main__.py`:

```python
import logging
from pathlib import Path

from .cleaner import DepsCleaner, build_parser

LOG_DIR = Path.home() / '.cache' / 'depscleaner'


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(LOG_DIR / 'depscleaner.log'),
            logging.StreamHandler(),
        ],
    )


def main():
    setup_logging()
    args = build_parser().parse_args()
    cleaner = DepsCleaner(path=args.path, depth=args.depth, dry_run=args.dry_run, yes=args.yes)
    cleaner.run()


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Smoke-test logging**

```bash
python3 -m depscleaner /nonexistent/path
cat ~/.cache/depscleaner/depscleaner.log
```

Expected: the log file exists, contains a line like `... WARNING depscleaner.cleaner: Invalid directory path: /nonexistent/path`, and no `error.log` is created in the CWD.

- [ ] **Step 4: Run the full suite**

Run: `python3 -m pytest -q`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "refactor: replace ad-hoc logger with stdlib logging to user cache dir"
```

---

### Task 9: Documentation and final verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the README**

Replace the whole `README.md`:

```markdown
# Depscleaner

Depscleaner is a CLI tool for finding and removing dependency directories like `node_modules` in your projects to free up space.

## Features

- Easy to add & change directory regexes (`DEPENDENCY_FOLDERS_REGEX` in `depscleaner/cleaner.py`)
- Error logging to `~/.cache/depscleaner/depscleaner.log`
- Dry-run mode to preview before deleting
- Interactive confirmation before any deletion

## Installation

```bash
pip install .
```

## Usage

```bash
depscleaner [path] [options]
```

| Option       | Description                                             |
| ------------ | ------------------------------------------------------- |
| `path`       | Root directory to scan (default: current directory)     |
| `--depth N`  | Maximum nesting depth to scan (default: 3)              |
| `--dry-run`  | Show what would be deleted without deleting anything    |
| `-y, --yes`  | Skip the interactive confirmation prompt                |
| `--version`  | Show the version                                         |

## Examples

```bash
depscleaner ~/projects
depscleaner ~/projects --depth 5
depscleaner ~/projects --dry-run
```
```

- [ ] **Step 2: Full verification pass**

```bash
python3 -m pytest -q
python3 -m depscleaner --version
python3 -m depscleaner . --dry-run
```

Expected: all tests pass, version prints, dry-run scans the current directory without deleting.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "docs: document new CLI flags and behavior"
```

---

## Self-Review Notes

- **Spec coverage:** every issue from the review is addressed — crash-safe input (Tasks 6, 7), symlink safety (Tasks 3, 4, 5), depth logic (Task 4), regex exactness (Task 4), confirmation/dry-run (Task 7), `shutil.rmtree` (Task 5), `argparse` (Task 6), logging location/timestamps (Task 8), size-race + unit labels (Task 3), dead code (Tasks 4, 7), and the packaging/entry-point break (Task 1).
- **Known accepted duplication:** `1.0.0` appears both in `depscleaner/__init__.py` and `setup.py`. Importing `__version__` from `setup.py` breaks in pip's isolated build env, so the literal is kept.
- **Type consistency:** `DepsCleaner(path=..., depth=..., dry_run=..., yes=...)` is used identically in `__main__.py` and all tests. `find_folders(path, depth)` has no third argument anywhere. `delete_folder` is the only deletion method (caller updated in Task 5).
