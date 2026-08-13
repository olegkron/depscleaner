import pytest

from depscleaner.cleaner import DepsCleaner


def sample_project(root):
    app = root / 'app'
    app.mkdir()
    (app / 'node_modules').mkdir()
    (app / 'vendor').mkdir()
    (app / 'src').mkdir()
    (app / 'node_modules' / 'x').mkdir()
    pkg = root / 'pkg'
    pkg.mkdir()
    (pkg / 'node_modules_old').mkdir()
    return root


def test_is_dependency_folder_exact_match_only():
    cleaner = DepsCleaner()
    assert cleaner.is_dependency_folder('node_modules')
    assert cleaner.is_dependency_folder('vendor')
    assert not cleaner.is_dependency_folder('node_modules_old')
    assert not cleaner.is_dependency_folder('src')


def test_find_folders_discovers_dependencies(tmp_path):
    root = sample_project(tmp_path)
    cleaner = DepsCleaner(path=str(root))
    cleaner.find_folders(cleaner.path, cleaner.depth)
    paths = {folder['path'] for folder in cleaner.found_folders}
    assert paths == {
        str(root / 'app' / 'node_modules'),
        str(root / 'app' / 'vendor'),
    }


def test_find_folders_does_not_descend_into_matched(tmp_path):
    root = sample_project(tmp_path)
    cleaner = DepsCleaner(path=str(root))
    cleaner.find_folders(cleaner.path, cleaner.depth)
    assert len(cleaner.found_folders) == 2


def test_find_folders_respects_depth(tmp_path):
    root = sample_project(tmp_path)
    (root / 'a' / 'b' / 'c' / 'node_modules').mkdir(parents=True)
    cleaner = DepsCleaner(path=str(root), depth=2)
    cleaner.find_folders(cleaner.path, cleaner.depth)
    paths = {folder['path'] for folder in cleaner.found_folders}
    assert str(root / 'a' / 'b' / 'c' / 'node_modules') not in paths


def test_find_folders_does_not_follow_symlinks(tmp_path):
    target = tmp_path / 'target'
    target.mkdir()
    (target / 'node_modules').mkdir()
    link = tmp_path / 'link'
    link.symlink_to(target, target_is_directory=True)
    cleaner = DepsCleaner(path=str(tmp_path))
    cleaner.find_folders(cleaner.path, cleaner.depth)
    assert len(cleaner.found_folders) == 1
    assert cleaner.found_folders[0]['path'] == str(target / 'node_modules')


def test_cleaner_default_depth_is_three():
    assert DepsCleaner.DEFAULT_DEPTH == 3


def test_delete_folder_removes_tree(tmp_path):
    dep = tmp_path / 'deps'
    (dep / 'a' / 'b').mkdir(parents=True)
    (dep / 'a' / 'f.txt').write_text('x')
    DepsCleaner().delete_folder(str(dep))
    assert not dep.exists()


def test_delete_folder_does_not_follow_symlinks(tmp_path):
    dep = tmp_path / 'deps'
    dep.mkdir()
    real = tmp_path / 'real'
    real.mkdir()
    (real / 'keep.txt').write_text('keep')
    (dep / 'link').symlink_to(real, target_is_directory=True)
    DepsCleaner().delete_folder(str(dep))
    assert not dep.exists()
    assert real.exists()
    assert (real / 'keep.txt').exists()


def test_build_parser_defaults():
    from depscleaner.cleaner import build_parser

    args = build_parser().parse_args([])
    assert args.path == '.'
    assert args.depth == DepsCleaner.DEFAULT_DEPTH
    assert args.dry_run is False
    assert args.yes is False


def test_build_parser_parses_flags():
    from depscleaner.cleaner import build_parser

    args = build_parser().parse_args(['/tmp/foo', '--depth', '5', '--dry-run', '--yes'])
    assert args.path == '/tmp/foo'
    assert args.depth == 5
    assert args.dry_run is True
    assert args.yes is True


def test_version_flag(capsys):
    from depscleaner.cleaner import build_parser

    with pytest.raises(SystemExit):
        build_parser().parse_args(['--version'])
    assert 'depscleaner' in capsys.readouterr().out
