import os

import obal
from obal.data.module_utils import obal as obal_utils
from obal.data.module_utils.obal import get_specfile_sources, get_changelog_evr
from obal.data.modules.repoclosure import build_command


def test_get_specfile_sources():
    sources = get_specfile_sources('tests/fixtures/testrepo/upstream/packages/hello/hello.spec')
    assert sources == ['http://ftp.gnu.org/gnu/hello/hello-2.10.tar.gz']


def test_get_specfile_sources_includes_patches(monkeypatch):
    def mock_run_command(command):
        assert command == ['spectool', '--list-files', '--all', 'package.spec']
        return 'Source0: https://example.com/source.tar.gz\nPatch0: fix.patch\n'

    monkeypatch.setattr(obal_utils, 'run_command', mock_run_command)

    assert get_specfile_sources('package.spec') == [
        'https://example.com/source.tar.gz',
        'fix.patch',
    ]


def test_get_changelog_evr():
    evr = get_changelog_evr('tests/fixtures/testrepo/upstream/packages/hello/hello.spec')
    assert evr == '2.10-2'


def test_inventory_packages():
    inventory = os.path.join(
        os.path.dirname(__file__),
        'fixtures/testrepo/upstream/package_manifest.yaml',
    )

    assert obal.inventory_items(inventory, 'list-packages') == [
        'bar',
        'broken-spec-package',
        'foo',
        'hello',
        'package-with-existing-build',
        'package-with-two-targets',
    ]


def test_inventory_groups():
    inventory = os.path.join(
        os.path.dirname(__file__),
        'fixtures/testrepo/copr/package_manifest.yaml',
    )

    assert obal.inventory_items(inventory, 'list-groups') == [
        'copr_projects',
        'packages',
        'repoclosures',
    ]


def test_list_packages_command(monkeypatch, capsys):
    inventory_dir = os.path.join(
        os.path.dirname(__file__),
        'fixtures/testrepo/upstream',
    )
    monkeypatch.chdir(inventory_dir)

    obal.main(['list-packages'])

    assert capsys.readouterr().out.splitlines() == [
        'bar',
        'broken-spec-package',
        'foo',
        'hello',
        'package-with-existing-build',
        'package-with-two-targets',
    ]


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
