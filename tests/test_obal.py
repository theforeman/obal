import pytest
import obal


@pytest.fixture
def playbooks_path(fixture_dir):
    return fixture_dir / 'playbooks'


@pytest.fixture
def application_config(playbooks_path):
    class MockApplicationConfig(obal.ApplicationConfig):
        @staticmethod
        def playbooks_path():
            return playbooks_path.strpath

    return MockApplicationConfig


@pytest.fixture
def parser(application_config, package_choices=['testpackage']):
    return obal.obal_argument_parser(application_config, package_choices=package_choices)


def test_find_no_packages(fixture_dir):
    packages = obal.find_packages((fixture_dir / 'nope.yaml').strpath)
    assert packages is None


def test_find_packages(fixture_dir):
    packages = obal.find_packages((fixture_dir / 'inventory.yaml').strpath)
    assert packages
    assert 'testpackage' in packages


def test_playbook_constructor(playbooks_path):
    path = (playbooks_path / 'setup' / 'setup.yaml').strpath
    playbook = obal.Playbook(path)
    assert playbook.path == path
    assert playbook.name == 'setup'


@pytest.mark.parametrize('playbook,expected', [
    ('setup', False),
    ('dummy', True),
    ('multiple_plays', True),
    ('repoclosure', True),
])
def test_playbook_takes_package_parameter(playbooks_path, playbook, expected):
    path = (playbooks_path / playbook / '{}.yaml'.format(playbook)).strpath
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
    (['dummy', 'testpackage', '--store-true'],
     ['--limit', 'testpackage', '-e', '{"store_true": true}']),
    (['dummy', 'testpackage', '--store-false'],
     ['--limit', 'testpackage', '-e', '{"store_false": false}']),
    (['dummy', 'testpackage', '--automatic', 'foo', '--explicit', 'bar'],
     ['--limit', 'testpackage', '-e', '{"automatic": "foo", "mapped": "bar"}']),
    (['dummy', 'testpackage', '--my-list', 'foo', '--my-list', 'bar'],
     ['--limit', 'testpackage', '-e', '{"mapped_list": ["foo", "bar"]}']),
])
def test_generate_ansible_args(playbooks_path, parser, cliargs, expected):
    action = cliargs[0]
    base_expected = [(playbooks_path / action / '{}.yaml'.format(action)).strpath,
                     '--inventory', 'inventory.yml']

    args = parser.parse_args(cliargs)
    ansible_args = obal.generate_ansible_args('inventory.yml', args, parser.obal_arguments)
    assert ansible_args == base_expected + expected


def test_obal_argument_parser_help(fixture_dir, parser):
    path = fixture_dir / 'help.txt'
    assert path.read() == parser.format_help()
