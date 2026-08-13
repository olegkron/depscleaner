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
    while size >= 1024 and suffix_index < len(suffixes) - 1:
        suffix_index += 1
        size /= 1024
    return f"{size:.{precision}f} {suffixes[suffix_index]}"
