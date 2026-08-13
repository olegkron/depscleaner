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


def test_build_parser_parses_flags():
    from depscleaner.cleaner import build_parser

    args = build_parser().parse_args(['/tmp/foo', '--depth', '5', '--dry-run'])
    assert args.path == '/tmp/foo'
    assert args.depth == 5
    assert args.dry_run is True


def test_version_flag(capsys):
    from depscleaner.cleaner import build_parser

    with pytest.raises(SystemExit):
        build_parser().parse_args(['--version'])
    assert 'depscleaner' in capsys.readouterr().out


class FakeTerminalMenu:
    selection = []

    def __init__(self, options, **kwargs):
        self.options = options
        self.kwargs = kwargs

    def show(self):
        return type(self).selection


def patch_input(monkeypatch, inputs):
    it = iter(inputs)
    monkeypatch.setattr('builtins.input', lambda _: next(it))


def patch_tty(monkeypatch, is_tty):
    monkeypatch.setattr('sys.stdin.isatty', lambda: is_tty)
    monkeypatch.setattr('sys.stdout.isatty', lambda: is_tty)


def test_run_does_not_prompt_when_nothing_found(tmp_path, monkeypatch):
    monkeypatch.setattr('builtins.input', lambda _: pytest.fail('must not prompt'))
    DepsCleaner(path=str(tmp_path)).run()


def test_menu_deletes_selected(tmp_path, monkeypatch, capsys):
    root = sample_project(tmp_path)
    monkeypatch.setattr('depscleaner.cleaner.TerminalMenu', FakeTerminalMenu)
    FakeTerminalMenu.selection = [0]
    patch_tty(monkeypatch, True)
    DepsCleaner(path=str(root)).run()
    assert not (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()
    assert 'Total space freed' in capsys.readouterr().out


def test_menu_quit_aborts(tmp_path, monkeypatch):
    root = sample_project(tmp_path)
    monkeypatch.setattr('depscleaner.cleaner.TerminalMenu', FakeTerminalMenu)
    FakeTerminalMenu.selection = None
    patch_tty(monkeypatch, True)
    DepsCleaner(path=str(root)).run()
    assert (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()


def test_menu_nothing_selected_deletes_nothing(tmp_path, monkeypatch, capsys):
    root = sample_project(tmp_path)
    monkeypatch.setattr('depscleaner.cleaner.TerminalMenu', FakeTerminalMenu)
    FakeTerminalMenu.selection = []
    patch_tty(monkeypatch, True)
    DepsCleaner(path=str(root)).run()
    assert (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()
    assert 'No folders selected' in capsys.readouterr().out


def test_fallback_deletes_selected(tmp_path, monkeypatch, capsys):
    root = sample_project(tmp_path)
    patch_tty(monkeypatch, False)
    patch_input(monkeypatch, ['0'])
    DepsCleaner(path=str(root)).run()
    assert not (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()
    assert 'Total space freed' in capsys.readouterr().out


def test_fallback_empty_input_aborts(tmp_path, monkeypatch):
    root = sample_project(tmp_path)
    patch_tty(monkeypatch, False)
    patch_input(monkeypatch, [''])
    DepsCleaner(path=str(root)).run()
    assert (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()


def test_fallback_reprompts_on_invalid(tmp_path, monkeypatch, capsys):
    root = sample_project(tmp_path)
    patch_tty(monkeypatch, False)
    patch_input(monkeypatch, ['banana', '0'])
    DepsCleaner(path=str(root)).run()
    assert not (root / 'app' / 'node_modules').exists()
    assert 'Invalid input' in capsys.readouterr().out


def test_fallback_ignores_out_of_range(tmp_path, monkeypatch, capsys):
    root = sample_project(tmp_path)
    patch_tty(monkeypatch, False)
    patch_input(monkeypatch, ['99 0'])
    DepsCleaner(path=str(root)).run()
    assert not (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()
    assert 'Ignoring out-of-range indices' in capsys.readouterr().out


def test_run_dry_run_deletes_nothing(tmp_path, capsys):
    root = sample_project(tmp_path)
    DepsCleaner(path=str(root), dry_run=True).run()
    assert (root / 'app' / 'node_modules').exists()
    assert (root / 'app' / 'vendor').exists()
    assert 'Dry run' in capsys.readouterr().out


def test_run_rejects_invalid_path(tmp_path, caplog):
    DepsCleaner(path=str(tmp_path / 'missing')).run()
    assert 'Invalid directory path' in caplog.text


def test_run_rejects_negative_depth(tmp_path, caplog):
    DepsCleaner(path=str(tmp_path), depth=-1).run()
    assert 'Invalid depth value' in caplog.text
