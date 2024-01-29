# depscleaner/depscleaner.py

import os
import re
from utils import calculate_directory_size, get_human_readable_size
from validator import validate_directory, validate_depth
from logger import log_error


class DepsCleaner:
    DEFAULT_DEPTH = 3
    DEPENDENCY_FOLDERS_REGEX = [r'node_modules', r'vendor']  # Add more regex patterns as needed

    def __init__(self, args):
        self.path = args[0] if args else '.'
        self.depth = int(args[1]) if len(args) > 1 else self.DEFAULT_DEPTH
        self.found_folders = []

    def run(self):
        if not validate_directory(self.path):
            log_error('Invalid directory path')
            return

        if not validate_depth(self.depth):
            log_error('Invalid depth value')
            return

        self.find_folders(self.path, self.depth)
        total_size = sum(folder['size'] for folder in self.found_folders)
        print(f"Total potential space to be freed: {get_human_readable_size(total_size)}")

        self.prompt_deletion()

    def find_folders(self, path, depth, current_depth=0):
        if depth == 0:
            return

        try:
            for entry in os.scandir(path):
                if entry.is_dir():
                    dir_name = os.path.basename(entry.path)
                    if any(re.match(pattern, dir_name) for pattern in self.DEPENDENCY_FOLDERS_REGEX):
                        dir_size = calculate_directory_size(entry.path)
                        self.found_folders.append({'path': entry.path, 'size': dir_size})
                        index = len(self.found_folders) - 1
                        print(f"[{index}] Found: {entry.path}, Size: {get_human_readable_size(dir_size)}")
                        # Do not continue searching inside this folder
                        continue
                    if current_depth < depth:
                        self.find_folders(entry.path, depth - 1, current_depth + 1)
        except Exception as e:
            log_error(f"Error scanning directory {path}: {e}")

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
                    log_error(f"Error deleting {folder['path']}: {e}")

        print(f"Total space freed: {get_human_readable_size(total_deleted_size)}")

    def recursive_delete(self, path):
        for entry in os.scandir(path):
            if entry.is_dir():
                self.recursive_delete(entry.path)
            else:
                os.unlink(entry.path)
        os.rmdir(path)
if __name__ == "__main__":
    import sys
    cleaner = DepsCleaner(sys.argv[1:])
    cleaner.run()
