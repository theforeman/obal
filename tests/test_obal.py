import os
import pytest
import obal
from pkg_resources import resource_filename


FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
)

DEFAULT_ARGS = ['dummy.yml', '--inventory', 'inventory.yml']


def test_find_no_packages():
    packages = obal.find_packages(os.path.join(FIXTURE_DIR, 'nope.yaml'))
    assert packages is None


def test_find_packages():
    packages = obal.find_packages(os.path.join(FIXTURE_DIR, 'inventory.yaml'))
    assert packages
    assert 'testpackage' in packages


def _test_generate_ansible_args(cliargs):
    playbooks_path = resource_filename('obal', 'data')
    playbooks = obal.find_playbooks(playbooks_path)
    parser = obal.obal_argument_parser(playbooks.keys(), ['testpackage'])
    args = parser.parse_args(cliargs)
    ansible_args = obal.generate_ansible_args('inventory.yml', 'dummy.yml',
                                              args)
    return ansible_args


def test_generate_ansible_args_none():
    with pytest.raises(SystemExit):
        _test_generate_ansible_args([])


@pytest.mark.parametrize('cliargs,expected', [
    (['scratch', 'testpackage'],
     DEFAULT_ARGS + ['--limit', 'testpackage']),
    (['--verbose', 'scratch', 'testpackage'],
     DEFAULT_ARGS + ['--limit', 'testpackage', '-v']),
    (['-vvvv', 'scratch', 'testpackage'],
     DEFAULT_ARGS + ['--limit', 'testpackage', '-vvvv']),
    (['--step', 'scratch', 'testpackage'],
     DEFAULT_ARGS + ['--limit', 'testpackage', '--step']),
    (['--skip-tags', 't1,t2', 'scratch', 'testpackage'],
     DEFAULT_ARGS + ['--limit', 'testpackage', '--skip-tags', 't1,t2']),
    (['--tags', 'wait,download', 'scratch', 'testpackage'],
     DEFAULT_ARGS + ['--limit', 'testpackage', '--tags', 'wait,download']),
    (['-e', 'v1=1', '-e', 'v2=2', 'scratch', 'testpackage'],
     DEFAULT_ARGS + ['--limit', 'testpackage', '-e', 'v1=1', '-e', 'v2=2']),
])
def test_generate_ansible_args(cliargs, expected):
    ansible_args = _test_generate_ansible_args(cliargs)
    assert ansible_args == expected
