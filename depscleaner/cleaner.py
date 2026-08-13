# depscleaner/cleaner.py

import argparse
import logging
import os
import re
import shutil

from . import __version__
from .utils import calculate_directory_size, get_human_readable_size
from .validator import validate_directory, validate_depth

logger = logging.getLogger(__name__)


class DepsCleaner:
    DEFAULT_DEPTH = 3
    DEPENDENCY_FOLDERS_REGEX = [r'node_modules', r'vendor']  # Add more regex patterns as needed

    def __init__(self, path='.', depth=DEFAULT_DEPTH, dry_run=False, yes=False):
        self.path = path
        self.depth = depth
        self.dry_run = dry_run
        self.yes = yes
        self.found_folders = []

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

    def delete_folder(self, path):
        shutil.rmtree(path)


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
