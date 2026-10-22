from dp_common import __version__, project_tag


def test_project_tag() -> None:
    assert project_tag() == "data-platform"


def test_version() -> None:
    assert isinstance(__version__, str)
    assert __version__
