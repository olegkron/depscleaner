def test_pytest_wiring():
    from depscleaner.utils import calculate_directory_size
    assert calculate_directory_size is not None
