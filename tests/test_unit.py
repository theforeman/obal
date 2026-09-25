import subprocess

import pytest

from obal.data.module_utils import obal
from obal.data.module_utils.obal import get_specfile_sources, get_changelog_evr
from obal.data.modules.repoclosure import build_command
from obal.data.modules import rpmspec_query


class ModuleFailure(Exception):
    def __init__(self, result):
        super().__init__(result['msg'])
        self.result = result


class FakeModule:
    def __init__(self):
        self.params = {
            'spec_file': 'package.spec',
            'query_format': '%{version}',
            'scl': None,
            'dist': None,
            'macros': None,
        }
        self.warnings = []

    def fail_json(self, **kwargs):
        raise ModuleFailure(kwargs)

    def warn(self, message):
        self.warnings.append(message)


def test_get_specfile_sources():
    sources = get_specfile_sources('tests/fixtures/testrepo/upstream/packages/hello/hello.spec')
    assert sources == ['http://ftp.gnu.org/gnu/hello/hello-2.10.tar.gz']


def test_get_specfile_sources_includes_patches(monkeypatch):
    def mock_run_command(command):
        assert command == ['spectool', '--list-files', '--all', 'package.spec']
        return 'Source0: https://example.com/source.tar.gz\nPatch0: fix.patch\n'

    monkeypatch.setattr(obal, 'run_command', mock_run_command)

    assert get_specfile_sources('package.spec') == [
        'https://example.com/source.tar.gz',
        'fix.patch',
    ]


def test_get_changelog_evr():
    evr = get_changelog_evr('tests/fixtures/testrepo/upstream/packages/hello/hello.spec')
    assert evr == '2.10-2'


def test_rpmspec_query_reports_failed_command_diagnostics(monkeypatch):
    def mock_lookup(*_args, **_kwargs):
        raise subprocess.CalledProcessError(
            1,
            ['rpmspec', 'package.spec'],
            output='',
            stderr='error: Unable to open package.spec',
        )

    monkeypatch.setattr(rpmspec_query, 'specfile_macro_lookup', mock_lookup)

    with pytest.raises(ModuleFailure) as failure:
        rpmspec_query.query_spec(FakeModule())

    assert failure.value.result['rc'] == 1
    assert failure.value.result['output'] == ''
    assert failure.value.result['stderr'] == 'error: Unable to open package.spec'


def test_rpmspec_query_rejects_incorrect_format(monkeypatch):
    monkeypatch.setattr(
        rpmspec_query,
        'specfile_macro_lookup',
        lambda *_args, **_kwargs: ('', 'error: incorrect format: unknown tag'),
    )

    with pytest.raises(ModuleFailure) as failure:
        rpmspec_query.query_spec(FakeModule())

    assert failure.value.result['msg'] == 'Invalid query_format for spec file'
    assert failure.value.result['stderr'] == 'error: incorrect format: unknown tag'


def test_rpmspec_query_warns_and_returns_value(monkeypatch):
    monkeypatch.setattr(
        rpmspec_query,
        'specfile_macro_lookup',
        lambda *_args, **_kwargs: ('1.2.3', 'warning: Macro expanded in comment\n'),
    )
    module = FakeModule()

    value = rpmspec_query.query_spec(module)

    assert value == '1.2.3'
    assert module.warnings == ['warning: Macro expanded in comment']


def test_repoclosure_build_command_no_excludes():
    command = build_command('repoclosure/yum.conf', ['repo0', 'el7-base'])

    assert '--setopt' not in ' '.join(command)


def test_repoclosure_build_command_exclude_repos_without_packages_is_noop():
    # exclude_repos with no exclude_packages (or vice versa) must not emit a
    # bare/broken --setopt - the cartesian product is simply empty.
    command = build_command('repoclosure/yum.conf', ['repo0'], exclude_repos=['el7-base'])

    assert '--setopt' not in ' '.join(command)


def test_repoclosure_build_command_excludes_only_target_repos():
    command = build_command(
        'repoclosure/yum.conf', ['repo0', 'el7-base'],
        additional_repos=[{'name': 'repo0', 'url': 'https://example.com/repo0'}],
        exclude_repos=['el7-base'],
        exclude_packages=['hello*'],
    )

    assert '--setopt=el7-base.excludepkgs=hello*' in command
    assert not any(opt.startswith('--setopt=repo0.') for opt in command)


def test_repoclosure_build_command_excludes_are_a_cartesian_product():
    command = build_command(
        'repoclosure/yum.conf', ['repo0'],
        exclude_repos=['el7-base', 'el7-katello'],
        exclude_packages=['hello*', 'world*'],
    )

    for repo in ('el7-base', 'el7-katello'):
        for package in ('hello*', 'world*'):
            assert '--setopt={}.excludepkgs={}'.format(repo, package) in command
