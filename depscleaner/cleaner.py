# depscleaner/cleaner.py

import logging
import os
import re

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
            logger.error('Invalid directory path')
            return

        if not validate_depth(self.depth):
            logger.error('Invalid depth value')
            return

        self.find_folders(self.path, self.depth)
        total_size = sum(folder['size'] for folder in self.found_folders)
        print(f"Total potential space to be freed: {get_human_readable_size(total_size)}")

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
        indices = input("Enter the indices of folders to delete (separated by space): ")
        selected_indices = set(map(int, indices.split()))

        total_deleted_size = 0
        for i in selected_indices:
            if 0 <= i < len(self.found_folders):
                folder = self.found_folders[i]
                try:
                    self.recursive_delete(folder['path'])
                    print(f"Deleted {folder['path']}")
                    total_deleted_size += folder['size']
                except Exception as e:
                    logger.error("Error deleting %s: %s", folder['path'], e)

        print(f"Total space freed: {get_human_readable_size(total_deleted_size)}")

    def recursive_delete(self, path):
        for entry in os.scandir(path):
            if entry.is_dir():
                self.recursive_delete(entry.path)
            else:
                os.unlink(entry.path)
        os.rmdir(path)
