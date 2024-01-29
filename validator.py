# depscleaner/validator.py

import os

def validate_directory(path):
    return os.path.exists(path) and os.path.isdir(path)

def validate_depth(depth):
    return isinstance(depth, int) and depth >= 0
