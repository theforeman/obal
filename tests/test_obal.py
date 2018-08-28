import os
import pytest
import obal


FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
)

DEFAULT_ARGS = [os.path.join(FIXTURE_DIR, 'playbooks', 'dummy.yml'),
                '--inventory', 'inventory.yml']


def test_find_no_packages():
    packages = obal.find_packages(os.path.join(FIXTURE_DIR, 'nope.yaml'))
    assert packages is None


def test_find_packages():
    packages = obal.find_packages(os.path.join(FIXTURE_DIR, 'inventory.yaml'))
    assert packages
    assert 'testpackage' in packages


def test_playbook_constructor():
    path = os.path.join(FIXTURE_DIR, 'playbooks', 'setup.yml')
    playbook = obal.Playbook(path)
    assert playbook.path == path
    assert playbook.name == 'setup'


def _test_generate_ansible_args(cliargs):
    playbooks = obal.find_playbooks(os.path.join(FIXTURE_DIR, 'playbooks'))
    parser = obal.obal_argument_parser(playbooks, ['testpackage'])
    args = parser.parse_args(cliargs)
    ansible_args = obal.generate_ansible_args('inventory.yml', args)
    return ansible_args


def test_generate_ansible_args_none():
    with pytest.raises(SystemExit):
        _test_generate_ansible_args([])


@pytest.mark.parametrize('cliargs,expected', [
    (['setup'],
     [os.path.join(FIXTURE_DIR, 'playbooks', 'setup.yml'), '--inventory', 'inventory.yml']),
    (['dummy', 'testpackage'],
     DEFAULT_ARGS + ['--limit', 'testpackage']),
    (['dummy', 'testpackage', '--verbose'],
     DEFAULT_ARGS + ['--limit', 'testpackage', '-v']),
    (['dummy', 'testpackage', '-vvvv'],
     DEFAULT_ARGS + ['--limit', 'testpackage', '-vvvv']),
    (['dummy', 'testpackage', '--step'],
     DEFAULT_ARGS + ['--limit', 'testpackage', '--step']),
    (['dummy', 'testpackage', '--skip-tags', 't1,t2'],
     DEFAULT_ARGS + ['--limit', 'testpackage', '--skip-tags', 't1,t2']),
    (['dummy', 'testpackage', '--tags', 'wait,download'],
     DEFAULT_ARGS + ['--limit', 'testpackage', '--tags', 'wait,download']),
    (['dummy', 'testpackage', '-e', 'v1=1', '-e', 'v2=2'],
     DEFAULT_ARGS + ['--limit', 'testpackage', '-e', 'v1=1', '-e', 'v2=2']),
])
def test_generate_ansible_args(cliargs, expected):
    ansible_args = _test_generate_ansible_args(cliargs)
    assert ansible_args == expected
