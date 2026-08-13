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
