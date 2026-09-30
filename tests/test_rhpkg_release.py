"""Promote public Foreman package versions as if Foreman used Brew.

Version provenance: theforeman/foreman-packaging, rpm/develop at
3aaa19d27f769214391072a2e1e595cf596d9f09 and rpm/5.0 at
9cca987afe60291a4165dff084c6bf2d4a728529. Specs are minimal local fixtures;
their Version/Release fields and foremandist contexts model those snapshots.
"""

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from obal.data.module_utils.rhpkg import build_info, inventory_tags, normalize_targets, ReleaseError


DEVELOP = 'foreman-develop-rhel-9-candidate'
DESTINATION = 'foreman-5.0-rhel-9-candidate'
SECONDARY = 'foreman-client-5.0-rhel-9-candidate'
PACKAGES = {
    'foreman_scap_client_bash': ('0.2.2', '1%{?dist}'),
    'nodejs-graphql': ('15.10.3', '1%{?dist}'),
    'yggdrasil-worker-forwarder': ('0.1.0', '2%{?dist}'),
    'rubygem-foreman_templates': ('11.0.4', '1%{?foremandist}%{?dist}'),
}


def git(directory, *arguments):
    return subprocess.check_output(['git', '-C', str(directory)] + list(arguments), text=True,
                                   stderr=subprocess.STDOUT).strip()


class BrewFixture:
    def __init__(self, root, monkeypatch):
        self.root = root
        self.repository = root / 'packaging'
        self.repository.mkdir()
        self.bin = root / 'bin'
        self.bin.mkdir()
        client = Path(__file__).parent / 'fixtures' / 'rhpkg' / 'mock_client.py'
        for name in ('brew', 'koji', 'rhpkg', 'tito', 'copr-cli'):
            executable = self.bin / name
            executable.write_text(client.read_text())
            executable.chmod(0o755)
        self.state_path = root / 'brew.json'
        self.write(dict(commands=[], builds={}, tasks={}, repositories={},
                        targets={DESTINATION: {'dist': '.el9', 'foremandist': '.fm5_0'}}))
        monkeypatch.setenv('OBAL_BREW_STATE', str(self.state_path))
        monkeypatch.setenv('PATH', str(self.bin) + os.pathsep + os.environ['PATH'])
        monkeypatch.setenv('PYTHONPATH', str(Path(__file__).resolve().parent.parent))
        git(self.repository, 'init', '--initial-branch=rpm/5.0')
        git(self.repository, 'config', 'user.name', 'Obal Test')
        git(self.repository, 'config', 'user.email', 'obal@example.test')
        git(self.repository, 'annex', 'init')
        self.target = dict(name='rhel9', distgit_branch='foreman-5.0-rhel-9',
                           build_target=DESTINATION, dist='.el9', macros={'foremandist': '.fm5_0'},
                           tags=[DESTINATION])

    def read(self):
        return json.loads(self.state_path.read_text())

    def write(self, state):
        self.state_path.write_text(json.dumps(state))

    def add(self, package, old=None):
        version, release = PACKAGES[package]
        directory = self.repository / 'packages' / package
        directory.mkdir(parents=True)
        spec = ('Name: {}\nVersion: {}\nRelease: {}\nSummary: Local release fixture\n'
                'License: MIT\nSource0: payload.txt\nPatch0: fix.patch\n'
                '%description\nLocal fixture.\n%files\n').format(package, version, release)
        (directory / (package + '.spec')).write_text(spec)
        (directory / 'payload.txt').write_text('new source content\n')
        (directory / 'fix.patch').write_text('fixture patch content\n')
        remote = self.root / (package + '.git')
        seed = self.root / (package + '-seed')
        seed.mkdir()
        git(seed, 'init', '--initial-branch=foreman-5.0-rhel-9')
        git(seed, 'config', 'user.name', 'Obal Test')
        git(seed, 'config', 'user.email', 'obal@example.test')
        if old:
            spec = spec.replace('Version: ' + version, 'Version: ' + old[0])
            spec = spec.replace('Release: ' + release, 'Release: ' + old[1])
        (seed / (package + '.spec')).write_text(spec.replace('Patch0: fix.patch', 'Patch0: old.patch'))
        (seed / 'old.patch').write_text('obsolete\n')
        (seed / 'gating.yaml').write_text('preserved\n')
        (seed / 'ci.fmf').write_text('preserved service configuration\n')
        git(seed, 'add', '.')
        git(seed, 'commit', '-m', '5.0 packaging')
        git(seed, 'clone', '--bare', str(seed), str(remote))
        state = self.read()
        state['repositories'][package] = str(remote)
        self.write(state)
        return directory

    def manifest(self, packages, targets=None, koji_executable=None):
        variables = dict(build_package_build_system='koji',
                         rhpkg_targets=targets or [self.target],
                         diff_package_tags=[DEVELOP], diff_package_skip=False,
                         ansible_python_interpreter=sys.executable)
        if koji_executable is not None:
            variables['build_package_koji_command'] = koji_executable
        data = {'packages': {'vars': variables, 'hosts': {name: {} for name in packages}}}
        (self.repository / 'package_manifest.yaml').write_text(yaml.safe_dump(data))
        git(self.repository, '-c', 'annex.largefiles=nothing', 'add', '.')
        git(self.repository, 'commit', '--allow-empty', '-m', 'Promote package versions into rpm/5.0')

    def release(self, package, *options, action='release', success=True):
        result = subprocess.run([sys.executable, '-c', 'import obal; obal.main()', action, package] + list(options),
                                cwd=self.repository, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                check=False)
        assert result.returncode == (0 if success else 2), result.stdout
        return result.stdout

    def existing(self, nvr, tags=None, state='COMPLETE'):
        data = self.read()
        data['builds'][nvr] = dict(state=state, tags=[DEVELOP] if tags is None else tags)
        self.write(data)

    def whitelist(self, parameters, success=True):
        root = Path(__file__).resolve().parent.parent / 'obal/data'
        playbook = self.root / 'whitelist.yaml'
        playbook.write_text(yaml.safe_dump([dict(hosts='localhost', gather_facts=False,
            vars={'ansible_python_interpreter': sys.executable},
            tasks=[{'package_whitelist_check': dict(parameters, build_command='brew')}])]))
        env = dict(os.environ, ANSIBLE_LIBRARY=str(root / 'modules'), ANSIBLE_MODULE_UTILS=str(root / 'module_utils'))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local', str(playbook)],
                                env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        assert result.returncode == (0 if success else 2), result.stdout
        return result.stdout


@pytest.fixture
def brew(tmp_path, monkeypatch):
    return BrewFixture(tmp_path, monkeypatch)


@pytest.mark.parametrize('action', ['release', 'scratch', 'check', 'verify-koji-tag'])
@pytest.mark.parametrize('executable', [None, 'koji'])
def test_rhpkg_workflows_default_to_brew_and_preserve_command_override(brew, action, executable):
    package = 'nodejs-graphql'
    brew.add(package)
    brew.manifest([package], koji_executable=executable)
    brew.release('all' if action == 'verify-koji-tag' else package, action=action)
    commands = brew.read()['commands']
    assert commands
    assert any(command[0] == (executable or 'brew') for command in commands)
    assert all(command[0] in (executable or 'brew', 'rhpkg') for command in commands)


@pytest.mark.parametrize('package,nvr', [
    ('foreman_scap_client_bash', 'foreman_scap_client_bash-0.2.2-1.el9'),
    ('nodejs-graphql', 'nodejs-graphql-15.10.3-1.el9'),
    ('yggdrasil-worker-forwarder', 'yggdrasil-worker-forwarder-0.1.0-2.el9'),
])
def test_promote_existing_develop_build_without_rebuilding(brew, package, nvr):
    brew.add(package)
    brew.manifest([package])
    brew.existing(nvr)
    brew.release(package)
    state = brew.read()
    assert set(state['builds'][nvr]['tags']) == {DEVELOP, DESTINATION}
    assert not any(command[0] == 'rhpkg' for command in state['commands'])
    assert not any('tito' in command or 'copr-cli' in command for command in state['commands'])
    brew.release(package)
    tags = [command for command in brew.read()['commands'] if command[1] == 'tag-build']
    assert tags == [['brew', 'tag-build', '--wait', DESTINATION, nvr]]


def test_missing_build_pushes_sources_then_builds_once_and_tags_all_destinations(brew):
    package = 'nodejs-graphql'
    brew.add(package, old=('15.10.2', '2%{?dist}'))
    brew.target['tags'].append(SECONDARY)
    brew.manifest([package])
    brew.release(package)
    state = brew.read()
    assert set(state['builds']['nodejs-graphql-15.10.3-1.el9']['tags']) == {DESTINATION, SECONDARY}
    assert len(state['tasks']) == 1
    remote = state['repositories'][package]
    spec = git(remote, 'show', 'HEAD:nodejs-graphql.spec')
    assert 'Version: 15.10.3' in spec and 'Release: 1%{?dist}' in spec
    assert git(remote, 'show', 'HEAD:fix.patch') == 'fixture patch content'
    assert git(remote, 'show', 'HEAD:gating.yaml') == 'preserved'
    assert git(remote, 'show', 'HEAD:ci.fmf') == 'preserved service configuration'
    assert 'old.patch' not in git(remote, 'ls-tree', '--name-only', 'HEAD')
    assert 'payload.txt' in git(remote, 'show', 'HEAD:sources')
    assert not any('--srpm' in command for command in state['commands'])
    assert state['builds']['nodejs-graphql-15.10.3-1.el9']['source'].endswith(git(remote, 'rev-parse', 'HEAD'))


def test_branch_macro_difference_requires_destination_nvr(brew):
    package = 'rubygem-foreman_templates'
    brew.add(package)
    brew.manifest([package])
    brew.existing(package + '-11.0.4-1.fm5_1.el9')
    brew.release(package)
    state = brew.read()
    assert state['builds'][package + '-11.0.4-1.fm5_1.el9']['tags'] == [DEVELOP]
    assert state['builds'][package + '-11.0.4-1.fm5_0.el9']['tags'] == [DESTINATION]
    assert len(state['tasks']) == 1


def test_nowait_receipt_resumes_before_build_record_exists(brew):
    package = 'nodejs-graphql'
    brew.add(package)
    brew.manifest([package])
    state = brew.read()
    state['delay_build_record'] = True
    brew.write(state)
    brew.release(package, '--nowait')
    receipt = json.loads((brew.repository / '.tmp/rhpkg/nodejs-graphql.json').read_text())
    assert receipt['targets']['rhel9']['pending_tags'] == [DESTINATION]
    assert not brew.read()['builds']
    brew.release(package)
    assert len(brew.read()['tasks']) == 1
    assert brew.read()['builds']['nodejs-graphql-15.10.3-1.el9']['tags'] == [DESTINATION]


def test_partial_tag_failure_can_be_retried_without_rebuilding(brew):
    package = 'foreman_scap_client_bash'
    nvr = package + '-0.2.2-1.el9'
    brew.add(package)
    brew.target['tags'].append(SECONDARY)
    brew.manifest([package])
    brew.existing(nvr)
    state = brew.read()
    state['failed_tags'] = [SECONDARY]
    brew.write(state)
    brew.release(package, success=False)
    state = brew.read()
    assert state['builds'][nvr]['tags'] == [DEVELOP, DESTINATION]
    state['failed_tags'] = []
    brew.write(state)
    brew.release(package)
    assert set(brew.read()['builds'][nvr]['tags']) == {DEVELOP, DESTINATION, SECONDARY}
    assert not brew.read()['tasks']


@pytest.mark.parametrize('failure', ['query_error', 'push_error'])
def test_errors_do_not_submit_a_build(brew, failure):
    package = 'nodejs-graphql'
    brew.add(package)
    brew.manifest([package])
    state = brew.read()
    state[failure] = True
    brew.write(state)
    brew.release(package, success=False)
    assert not brew.read()['tasks']


def test_failed_build_is_not_resubmitted(brew):
    package = 'nodejs-graphql'
    brew.add(package)
    brew.manifest([package])
    brew.existing(package + '-15.10.3-1.el9', state='FAILED')
    brew.release(package, success=False)
    assert not brew.read()['tasks']


def test_scratch_submits_all_targets_before_waiting_and_never_tags(brew):
    package = 'nodejs-graphql'
    brew.add(package)
    second = copy.deepcopy(brew.target)
    second.update(name='rhel10', build_target='foreman-5.0-rhel-10-candidate', dist='.el10',
                  tags=['foreman-5.0-rhel-10-candidate'])
    brew.target['tags'].append(SECONDARY)
    brew.manifest([package], [brew.target, second])
    state = brew.read()
    state['targets'][second['build_target']] = dict(dist='.el10', foremandist='.fm5_0')
    state['failed_targets'] = [DESTINATION]
    brew.write(state)
    original = git(state['repositories'][package], 'rev-parse', 'HEAD')
    brew.release(package, action='scratch', success=False)
    state = brew.read()
    assert len(state['tasks']) == 2
    submissions = [i for i, command in enumerate(state['commands']) if command[:2] == ['brew', 'build']]
    waits = [i for i, command in enumerate(state['commands']) if command[1] == 'watch-task']
    assert max(submissions) < min(waits)
    assert not any(command[1] in ['new-sources', 'commit', 'push', 'tag-build'] for command in state['commands'])
    assert not any(command[0] == 'rhpkg' for command in state['commands'])
    assert not state['builds']
    assert git(state['repositories'][package], 'rev-parse', 'HEAD') == original


def test_normalization_preserves_build_and_tag_distinction():
    target = dict(name='rhel9', distgit_branch='foreman-5.0-rhel-9', build_target=DESTINATION,
                  dist='.el9', tags=[DESTINATION, SECONDARY])
    attributes = dict(build_package_releaser='rhpkg', rhpkg_targets=[target])
    assert len(normalize_targets([target], 'package')) == 1
    assert [tag['name'] for tag in inventory_tags(attributes, 'package')] == [DESTINATION, SECONDARY]
    equivalent = [dict(name=name, dist='.el9') for name in (SECONDARY, DESTINATION)]
    assert inventory_tags(dict(attributes, koji_tags=equivalent), 'package') == inventory_tags(attributes, 'package')
    with pytest.raises(ReleaseError, match='conflicts'):
        inventory_tags(dict(attributes, koji_tags=[{'name': 'wrong'}]), 'package')


def test_check_compares_destination_even_when_develop_has_the_build(brew):
    package = 'foreman_scap_client_bash'
    nvr = package + '-0.2.2-1.el9'
    brew.add(package)
    brew.manifest([package])
    brew.existing(nvr)
    output = brew.release(package, action='check')
    assert 'changed: true' in output
    assert brew.read()['builds'][nvr]['tags'] == [DEVELOP]
    assert not any(command[0] == 'rhpkg' or command[1] == 'tag-build' for command in brew.read()['commands'])
    assert not (brew.repository / '.tmp/rhpkg').exists()


def test_release_only_change_builds_the_new_release(brew):
    package = 'yggdrasil-worker-forwarder'
    brew.add(package, old=('0.1.0', '1%{?dist}'))
    brew.manifest([package])
    brew.existing(package + '-0.1.0-1.el9', tags=[DESTINATION])
    brew.release(package)
    assert len(brew.read()['tasks']) == 1
    assert brew.read()['builds'][package + '-0.1.0-2.el9']['tags'] == [DESTINATION]


def test_resume_rejects_changed_source_bytes(brew):
    package = 'nodejs-graphql'
    directory = brew.add(package)
    brew.manifest([package])
    state = brew.read()
    state['delay_build_record'] = True
    brew.write(state)
    brew.release(package, '--nowait')
    (directory / 'payload.txt').write_text('changed after submission\n')
    output = brew.release(package, success=False)
    assert 'sources changed' in output
    assert len(brew.read()['tasks']) == 1
    (directory / 'payload.txt').write_text('new source content\n')
    brew.release(package)
    assert len(brew.read()['tasks']) == 1
    assert brew.read()['builds'][package + '-15.10.3-1.el9']['tags'] == [DESTINATION]


def test_reused_build_supports_waitrepo_and_downloads(brew):
    package = 'foreman_scap_client_bash'
    nvr = package + '-0.2.2-1.el9'
    brew.add(package)
    brew.manifest([package])
    brew.existing(nvr)
    brew.release(package, '-e', 'build_package_waitrepo=true', '-e', 'build_package_download_rpms=true')
    commands = brew.read()['commands']
    assert ['brew', 'wait-repo', '--build=' + nvr, '--target', DESTINATION] in commands
    assert ['brew', 'download-build', nvr] in commands
    assert not brew.read()['tasks']


def test_conflicting_releasers_fail_before_submission(brew):
    package = 'nodejs-graphql'
    brew.add(package)
    brew.manifest([package])
    brew.release(package, '-e', 'build_package_releaser=rhpkg',
                 '-e', 'build_package_use_koji_build=true', success=False)
    assert not brew.read()['commands']


def test_verify_tags_uses_rhpkg_destinations_and_brew(brew):
    package = 'foreman_scap_client_bash'
    brew.add(package)
    brew.target['tags'].append(SECONDARY)
    brew.manifest([package])
    brew.release('all', action='verify-koji-tag')
    commands = brew.read()['commands']
    assert ['brew', 'list-pkgs', '--quiet', '--tag', DESTINATION] in commands
    assert ['brew', 'list-pkgs', '--quiet', '--tag', SECONDARY] in commands


def test_submission_error_still_attempts_other_targets(brew):
    package = 'nodejs-graphql'
    brew.add(package)
    second = copy.deepcopy(brew.target)
    second.update(name='rhel10', build_target='foreman-5.0-rhel-10-candidate', dist='.el10',
                  tags=['foreman-5.0-rhel-10-candidate'])
    brew.manifest([package], [brew.target, second])
    state = brew.read()
    state['targets'][second['build_target']] = dict(dist='.el10', foremandist='.fm5_0')
    state['submission_errors'] = [DESTINATION]
    brew.write(state)
    brew.release(package, success=False)
    assert len(brew.read()['tasks']) == 1
    assert brew.read()['builds'][package + '-15.10.3-1.el10']['tags'] == [second['build_target']]


def test_query_failure_is_not_a_missing_build(brew):
    state = brew.read()
    state['query_error'] = True
    brew.write(state)
    with pytest.raises(ReleaseError, match='Authentication failed'):
        build_info('brew', 'package-1-1.el9')


@pytest.mark.parametrize('action', ['release', 'scratch'])
def test_build_downloads_logs_and_rpms_without_tito(brew, action):
    package = 'nodejs-graphql'
    brew.add(package)
    brew.manifest([package])
    brew.release(package, '-e', 'build_package_download_logs=true',
                 '-e', 'build_package_download_rpms=true', action=action)
    state = brew.read()
    task = next(iter(state['tasks']))
    assert ['brew', 'download-logs', '-r', task] in state['commands']
    expected = (['brew', 'download-task', '--arch=noarch', '--arch=x86_64', task] if action == 'scratch'
                else ['brew', 'download-build', package + '-15.10.3-1.el9'])
    assert expected in state['commands']
    assert not any(command[0] == 'tito' for command in state['commands'])


def test_scratch_nowait_resumes_pending_task_without_release_mutations(brew):
    package = 'nodejs-graphql'
    brew.add(package)
    brew.manifest([package])
    brew.release(package, '-e', 'build_package_wait=false', action='scratch')
    state = brew.read()
    assert len(state['tasks']) == 1
    assert not state['builds']
    assert not any(command[1] in ('watch-task', 'tag-build', 'new-sources', 'commit', 'push')
                   for command in state['commands'])
    receipt_path = brew.repository / '.tmp/rhpkg/nodejs-graphql-scratch.json'
    receipt = json.loads(receipt_path.read_text())
    assert receipt['targets']['rhel9']['state'] == 'PENDING'
    assert receipt['targets']['rhel9']['pending_tags'] == []
    task_id = receipt['targets']['rhel9']['tasks'][0]

    brew.release(package, '-e', 'build_package_wait=false', action='scratch')
    assert len(brew.read()['tasks']) == 1
    assert json.loads(receipt_path.read_text())['targets']['rhel9']['tasks'] == [task_id]

    brew.release(package, '-e', 'build_package_download_logs=true',
                 '-e', 'build_package_download_rpms=true', action='scratch')
    state = brew.read()
    assert len(state['tasks']) == 1
    assert state['tasks'][task_id]['state'] == 'closed'
    assert ['brew', 'watch-task', task_id] in state['commands']
    assert ['brew', 'download-logs', '-r', task_id] in state['commands']
    assert ['brew', 'download-task', '--arch=noarch', '--arch=x86_64', task_id] in state['commands']
    assert json.loads(receipt_path.read_text())['targets']['rhel9']['state'] == 'COMPLETE'
    assert not state['builds']
    assert not any(command[0] == 'rhpkg' or command[1] in ('buildinfo', 'list-pkgs', 'tag-build')
                   for command in state['commands'])

    # A completed scratch receipt must allow a genuinely new scratch build.
    brew.release(package, action='scratch')
    assert len(brew.read()['tasks']) == 2


@pytest.mark.parametrize('change', ['source', 'spec', 'nvr', 'target'])
def test_scratch_resume_rejects_changed_inputs_and_preserves_receipt(brew, change):
    package = 'nodejs-graphql'
    directory = brew.add(package)
    brew.manifest([package])
    brew.release(package, '-e', 'build_package_wait=false', action='scratch')
    receipt_path = brew.repository / '.tmp/rhpkg/nodejs-graphql-scratch.json'
    receipt = receipt_path.read_bytes()
    if change == 'source':
        changed_file = directory / 'payload.txt'
        original = changed_file.read_text()
        changed_file.write_text('changed after submission\n')
    elif change in ('spec', 'nvr'):
        changed_file = directory / (package + '.spec')
        original = changed_file.read_text()
        changed_file.write_text(original + '# Changed spec\n' if change == 'spec'
                                else original.replace('Version: 15.10.3', 'Version: 15.10.4'))
    else:
        changed_file = brew.repository / 'package_manifest.yaml'
        original = changed_file.read_text()
        manifest = yaml.safe_load(original)
        manifest['packages']['vars']['rhpkg_targets'][0]['build_target'] = SECONDARY
        changed_file.write_text(yaml.safe_dump(manifest))
    output = brew.release(package, action='scratch', success=False)
    assert 'pending' in output
    assert len(brew.read()['tasks']) == 1
    assert receipt_path.read_bytes() == receipt
    assert not any(command[1] in ('buildinfo', 'tag-build', 'watch-task') for command in brew.read()['commands'])
    changed_file.write_text(original)
    brew.release(package, action='scratch')
    assert len(brew.read()['tasks']) == 1
    assert json.loads(receipt_path.read_text())['targets']['rhel9']['state'] == 'COMPLETE'


@pytest.mark.parametrize('registered', [True, False])
def test_tag_registration_checked_before_submission(brew, registered):
    package = 'nodejs-graphql'
    brew.add(package)
    brew.manifest([package])
    state = brew.read()
    state['unregistered'] = not registered
    brew.write(state)
    brew.release(package, '-e', 'build_package_koji_whitelist_check=true', success=registered)
    state = brew.read()
    assert ['brew', 'list-pkgs', '--tag', DESTINATION, '--package', package, '--quiet'] in state['commands']
    assert len(state['tasks']) == int(registered)


@pytest.mark.parametrize('action', ['release', 'scratch'])
def test_tito_selector_is_rejected(brew, action):
    package = 'nodejs-graphql'
    brew.add(package)
    brew.manifest([package])
    output = brew.release(package, '-e', 'build_package_releaser=tito', action=action, success=False)
    assert 'Tito releases are no longer supported' in output
    assert not brew.read()['commands']


def test_legacy_brew_inventory_requires_explicit_distgit_targets(brew):
    package = 'nodejs-graphql'
    brew.add(package)
    brew.manifest([package])
    manifest = brew.repository / 'package_manifest.yaml'
    data = yaml.safe_load(manifest.read_text())
    del data['packages']['vars']['rhpkg_targets']
    data['packages']['vars']['releasers'] = ['foreman-5.0-dist-git']
    manifest.write_text(yaml.safe_dump(data))
    output = brew.release(package, success=False)
    assert 'rhpkg_targets must contain at least one build target' in output
    assert not brew.read()['commands']


@pytest.mark.parametrize('failure', ['unregistered_tags', 'blocked_tags', 'registration_error'])
def test_existing_build_is_not_tagged_without_destination_registration(brew, failure):
    package = 'nodejs-graphql'
    nvr = package + '-15.10.3-1.el9'
    brew.add(package)
    brew.target['tags'].append(SECONDARY)
    brew.manifest([package])
    brew.existing(nvr)
    state = brew.read()
    state[failure] = [SECONDARY] if failure.endswith('_tags') else True
    brew.write(state)
    output = brew.release(package, success=False)
    assert 'registration' in output or 'not registered' in output
    state = brew.read()
    assert state['builds'][nvr]['tags'] == [DEVELOP]
    assert not any(command[0] == 'rhpkg' or command[1] == 'tag-build' for command in state['commands'])


@pytest.mark.parametrize('legacy', [True, False])
@pytest.mark.parametrize('registered', [True, False])
def test_whitelist_module_supports_explicit_tags_and_legacy_config(brew, legacy, registered):
    package = 'nodejs-graphql'
    directory = brew.add(package)
    state = brew.read()
    state['unregistered_tags'] = [] if registered else [SECONDARY]
    brew.write(state)
    if legacy:
        config = brew.root / 'releasers.conf'
        config.write_text('[release]\nbranches={}\n[client]\nautobuild_tags={}\n'.format(DESTINATION, SECONDARY))
        parameters = dict(releasers_conf=str(config), releasers=['release', 'client'],
                          spec_file_path=str(directory / (package + '.spec')))
    else:
        parameters = dict(package=package, tags=[DESTINATION, SECONDARY])
    brew.whitelist(parameters, success=registered)
    commands = brew.read()['commands']
    assert ['brew', 'list-pkgs', '--tag', DESTINATION, '--package', package, '--quiet'] in commands
    assert ['brew', 'list-pkgs', '--tag', SECONDARY, '--package', package, '--quiet'] in commands
    assert all(command[:2] == ['brew', 'list-pkgs'] for command in commands)


def test_koji_scratch_fetches_annex_bytes_without_registration_or_rhpkg(brew):
    package = 'nodejs-graphql'
    directory = brew.add(package)
    source = directory / 'payload.txt'
    payload = source.read_bytes()
    relative = str(source.relative_to(brew.repository))
    remote = brew.root / 'annex-source-remote'
    remote.mkdir()
    git(brew.repository, 'annex', 'initremote', 'sources', 'type=directory',
        'directory=' + str(remote), 'encryption=none')
    git(brew.repository, 'annex', 'add', '--force-large', relative)
    brew.manifest([package])
    git(brew.repository, 'annex', 'copy', '--to=sources', '--', relative)
    git(brew.repository, 'annex', 'drop', '--', relative)
    assert source.is_symlink() and not source.exists()
    state = brew.read()
    state['unregistered'] = True
    brew.write(state)
    brew.release(package, '-e', 'build_package_koji_whitelist_check=true', action='scratch')
    state = brew.read()
    task = next(iter(state['tasks'].values()))
    assert task['source_sha256'] == hashlib.sha256(payload).hexdigest()
    assert source.is_symlink() and source.read_bytes() == payload
    assert any(command[:4] == ['brew', 'build', '--scratch', '--nowait'] for command in state['commands'])
    assert not any(command[0] == 'rhpkg' or command[1] in ('list-pkgs', 'tag-build') for command in state['commands'])
