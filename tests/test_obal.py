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
def parser(application_config, targets=['testpackage']):
    return obal.obal_argument_parser(application_config, targets=targets)


def test_find_no_targets(fixture_dir):
    targets = obal.find_targets((fixture_dir / 'nope.yaml').strpath)
    assert targets is None


def test_find_targets(fixture_dir):
    targets = obal.find_targets((fixture_dir / 'inventory.yaml').strpath)
    assert targets
    assert 'testpackage' in targets


def test_playbook_constructor(application_config, playbooks_path):
    path = (playbooks_path / 'setup' / 'setup.yaml').strpath
    playbook = obal.Playbook(path, application_config)
    assert playbook.path == path
    assert playbook.name == 'setup'


@pytest.mark.parametrize('playbook,expected', [
    ('setup', False),
    ('dummy', True),
    ('multiple_plays', True),
    ('repoclosure', True),
])
def test_playbook_takes_target_parameter(application_config, playbooks_path, playbook, expected):
    path = (playbooks_path / playbook / '{}.yaml'.format(playbook)).strpath
    assert obal.Playbook(path, application_config).takes_target_parameter == expected


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
