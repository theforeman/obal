import pytest
import obal


@pytest.fixture
def playbooks(fixture_dir):
    return obal.find_playbooks((fixture_dir / 'playbooks').strpath)


@pytest.fixture
def parser(playbooks, package_choices=['testpackage']):
    return obal.obal_argument_parser(playbooks, package_choices)


def test_find_no_packages(fixture_dir):
    packages = obal.find_packages((fixture_dir / 'nope.yaml').strpath)
    assert packages is None


def test_find_packages(fixture_dir):
    packages = obal.find_packages((fixture_dir / 'inventory.yaml').strpath)
    assert packages
    assert 'testpackage' in packages


def test_playbook_constructor(fixture_dir):
    path = (fixture_dir / 'playbooks' / 'setup' / 'setup.yaml').strpath
    playbook = obal.Playbook(path)
    assert playbook.path == path
    assert playbook.name == 'setup'


@pytest.mark.parametrize('playbook,expected', [
    ('setup', False),
    ('dummy', True),
    ('multiple_plays', True),
    ('repoclosure', True),
])
def test_playbook_takes_package_parameter(fixture_dir, playbook, expected):
    path = (fixture_dir / 'playbooks' / playbook / '{}.yaml'.format(playbook)).strpath
    assert obal.Playbook(path).takes_package_parameter == expected


def test_parser_no_arguments(parser):
    with pytest.raises(SystemExit):
        parser.parse_args([])


@pytest.mark.parametrize('cliargs,expected', [
    (['setup'],
     []),
    (['dummy', 'testpackage'],
     ['--limit', 'testpackage']),
    (['dummy', 'testpackage', '--verbose'],
     ['--limit', 'testpackage', '-v']),
    (['dummy', 'testpackage', '-vvvv'],
     ['--limit', 'testpackage', '-vvvv']),
    (['dummy', 'testpackage', '-e', 'v1=1', '-e', 'v2=2'],
     ['--limit', 'testpackage', '-e', 'v1=1', '-e', 'v2=2']),
    (['dummy', 'testpackage', '--automatic', 'foo'],
     ['--limit', 'testpackage', '-e', '{"automatic": "foo"}']),
    (['dummy', 'testpackage', '--explicit', 'foo'],
     ['--limit', 'testpackage', '-e', '{"mapped": "foo"}']),
    (['dummy', 'testpackage', '--automatic', 'foo', '--explicit', 'bar'],
     ['--limit', 'testpackage', '-e', '{"automatic": "foo", "mapped": "bar"}']),
])
def test_generate_ansible_args(fixture_dir, parser, cliargs, expected):
    action = cliargs[0]
    base_expected = [(fixture_dir / 'playbooks' / action / '{}.yaml'.format(action)).strpath,
                     '--inventory', 'inventory.yml']

    args = parser.parse_args(cliargs)
    ansible_args = obal.generate_ansible_args('inventory.yml', args)
    assert ansible_args == base_expected + expected


def test_obal_argument_parser_help(fixture_dir, parser):
    path = fixture_dir / 'help.txt'
    assert path.read() == parser.format_help()
