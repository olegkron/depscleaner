# depscleaner/__main__.py

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
