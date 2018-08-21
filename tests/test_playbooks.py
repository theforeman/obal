import os

import pytest

import obal


@pytest.fixture
def help_dir(fixture_dir):
    return fixture_dir / 'help'


def playbook_id(fixture_value):
    return fixture_value.name


@pytest.fixture(params=obal.find_playbooks(obal.get_playbooks_path()), ids=playbook_id)
def playbook(request):
    yield request.param


def test_takes_package_argument(playbook):
    expected = playbook.name not in ('setup', 'cleanup-copr')
    assert playbook.takes_package_parameter == expected


def test_is_documented(playbook):
    assert playbook.help_text is not None


def test_filename_matches_directory(playbook):
    filename = os.path.splitext(os.path.basename(playbook.path))[0]
    dirname = os.path.basename(os.path.dirname(playbook.path))
    assert filename == dirname
