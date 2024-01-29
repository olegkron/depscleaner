# depscleaner/__main__.py

import sys
from .depscleaner import DepsCleaner

def main():
    try:
        deps_cleaner = DepsCleaner(sys.argv[1:])
        deps_cleaner.run()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
