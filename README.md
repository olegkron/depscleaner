# Depscleaner

Depscleaner is a CLI tool for finding and removing dependency directories like `node_modules` in your projects to free up space.

## Features

- Easy to add & change directory regexes (`DEPENDENCY_FOLDERS_REGEX` in `depscleaner/cleaner.py`)
- Error logging to `~/.cache/depscleaner/depscleaner.log`
- Dry-run mode to preview before deleting
- Arrow-key interactive selection: move with arrows, toggle with `space`, confirm with `enter`, quit with `q`/`esc`
  (falls back to a numeric prompt when stdin is not a TTY, e.g. piped or CI)

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
| `--version`  | Show the version                                         |

## Examples

```bash
depscleaner ~/projects
depscleaner ~/projects --depth 5
depscleaner ~/projects --dry-run
```
