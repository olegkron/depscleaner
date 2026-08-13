from depscleaner.utils import calculate_directory_size, get_human_readable_size


def test_pytest_wiring():
    assert calculate_directory_size is not None


def test_size_zero():
    assert get_human_readable_size(0) == '0.00 B'


def test_size_exact_kib():
    assert get_human_readable_size(1024) == '1.00 KiB'


def test_size_fraction_kib():
    assert get_human_readable_size(1536) == '1.50 KiB'


def test_size_round_trips():
    assert get_human_readable_size(1) == '1.00 B'


def test_calculate_directory_size_recurses(tmp_path):
    (tmp_path / 'a.txt').write_text('x' * 100)
    sub = tmp_path / 'sub'
    sub.mkdir()
    (sub / 'b.txt').write_text('y' * 200)
    assert calculate_directory_size(str(tmp_path)) == 300


def test_calculate_directory_size_ignores_symlinked_dir(tmp_path):
    real = tmp_path / 'real'
    real.mkdir()
    (real / 'f.txt').write_text('x' * 500)
    link = tmp_path / 'link'
    link.symlink_to(real, target_is_directory=True)
    assert calculate_directory_size(str(tmp_path)) == 500
