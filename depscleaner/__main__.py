# depscleaner/__main__.py

import sys
from .cleaner import DepsCleaner

def main():
    try:
        path = sys.argv[1] if len(sys.argv) > 1 else '.'
        depth = int(sys.argv[2]) if len(sys.argv) > 2 else DepsCleaner.DEFAULT_DEPTH
        deps_cleaner = DepsCleaner(path=path, depth=depth)
        deps_cleaner.run()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
