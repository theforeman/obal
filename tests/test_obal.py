import os
import pytest
import obal


FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
)


def test_find_no_packages():
    packages = obal.find_packages(os.path.join(FIXTURE_DIR, 'nope.yaml'))
    assert packages is None


def test_find_packages():
    packages = obal.find_packages(os.path.join(FIXTURE_DIR, 'inventory.yaml'))
    assert packages
    assert 'testpackage' in packages


def _test_generate_ansible_args(cliargs):
    parser = obal.obal_argument_parser(['testpackage'])
    args = parser.parse_args(cliargs)
    ansible_args = obal.generate_ansible_args('inventory.yml', 'dummy.yml',
                                              args)
    return ansible_args


def test_generate_ansible_args_none():
    with pytest.raises(SystemExit):
        _test_generate_ansible_args([])


def test_generate_ansible_args_testpackage():
    ansible_args = _test_generate_ansible_args(['scratch', 'testpackage'])
    assert 'testpackage' in ansible_args


def test_generate_ansible_args_tags():
    cliargs = ['--tags', 'wait,download', 'scratch', 'testpackage']
    ansible_args = _test_generate_ansible_args(cliargs)
    assert 'testpackage' in ansible_args
    assert '--tags' in ansible_args
    assert 'wait,download' in ansible_args
