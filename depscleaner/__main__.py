# depscleaner/__main__.py

from .cleaner import DepsCleaner, build_parser


def main():
    args = build_parser().parse_args()
    cleaner = DepsCleaner(path=args.path, depth=args.depth, dry_run=args.dry_run, yes=args.yes)
    cleaner.run()


if __name__ == '__main__':
    main()
