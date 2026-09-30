"""Release dist-git packages through rhpkg and reconcile Koji build tags."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit

from ansible.module_utils.parsing.convert_bool import boolean

try:
    from ansible.module_utils.obal import specfile_macro_lookup
    from ansible.module_utils.koji_wrapper import package_whitelisted, KojiCommandError
except ImportError:
    from .obal import specfile_macro_lookup
    from .koji_wrapper import package_whitelisted, KojiCommandError


class ReleaseError(Exception):
    """A release could not be completed."""


def run(command, directory=None, check=True):
    """Run an argument vector, preserving command diagnostics."""
    result = subprocess.run(command, cwd=directory, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, env=dict(os.environ, LC_ALL='C'), check=False)
    if check and result.returncode:
        raise ReleaseError('{} failed ({}): {}'.format(command, result.returncode, result.stdout))
    return result


def normalize_targets(targets, package):
    """Validate explicit build destinations independently of output tags."""
    if not isinstance(targets, list) or not targets:
        raise ReleaseError('rhpkg_targets must contain at least one build target')
    normalized = []
    names = set()
    for value in targets:
        if not isinstance(value, dict):
            raise ReleaseError('Each rhpkg target must be a dictionary')
        target = dict(value)
        target.setdefault('distgit_package', package)
        target.setdefault('macros', {})
        for key in ('name', 'distgit_package', 'distgit_branch', 'build_target', 'dist'):
            if not isinstance(target.get(key), str) or not target[key] or target[key].startswith('-'):
                raise ReleaseError('Each rhpkg target requires a nonempty {}'.format(key))
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', target['name']) or target['name'] in names:
            raise ReleaseError('rhpkg target names must be unique path-safe identifiers')
        names.add(target['name'])
        if not isinstance(target['macros'], dict):
            raise ReleaseError('rhpkg target macros must be a dictionary')
        if set(target['macros']) & {'dist', 'scl'}:
            raise ReleaseError('Use the target dist and scl fields instead of redefining them in macros')
        tags = target.get('tags')
        if not isinstance(tags, list) or not tags or any(
                not isinstance(tag, str) or not tag or tag.startswith('-') for tag in tags):
            raise ReleaseError('Each rhpkg target requires a nonempty list of destination tag names')
        target['tags'] = list(dict.fromkeys(tags))
        normalized.append(target)
    return normalized


def uses_rhpkg(attributes):
    """Recognize configured dist-git targets outside build role defaults."""
    direct = boolean(attributes.get('build_package_use_koji_build', False))
    default = 'rhpkg' if attributes.get('rhpkg_targets') and not direct else 'koji'
    return attributes.get('build_package_releaser', default) == 'rhpkg'


def inventory_tags(attributes, package):
    """Expose the same tag configuration to release and inventory verification."""
    if not uses_rhpkg(attributes):
        return attributes.get('koji_tags', [])
    tags = []
    for target in normalize_targets(attributes.get('rhpkg_targets'), package):
        for name in target['tags']:
            tag = {key: target[key] for key in ('dist', 'scl', 'macros') if key in target}
            tags.append(dict(tag, name=name))
    configured = attributes.get('koji_tags', [])
    def comparable(values):
        return {json.dumps({key: value.get(key, {} if key == 'macros' else None)
                            for key in ('name', 'dist', 'scl', 'macros')}, sort_keys=True) for value in values}
    if configured and comparable(configured) != comparable(tags):
        raise ReleaseError('koji_tags conflicts with rhpkg_targets; configure the destination tags in rhpkg_targets')
    return tags


def build_info(executable, nvr):
    """Distinguish an absent build from a failed query or an incomplete build."""
    result = run([executable, 'buildinfo', nvr], check=False)
    if result.returncode:
        if result.stdout.strip() == 'No such build: {}'.format(nvr):
            return {'state': 'MISSING', 'tags': [], 'task': None, 'source': None}
        raise ReleaseError('Unable to query {}: {}'.format(nvr, result.stdout))
    fields = dict(re.findall(r'^(BUILD|State|Tags|Task|Source):[ \t]*(.*)$', result.stdout, re.MULTILINE))
    if fields.get('BUILD', '').split(' ', 1)[0] != nvr or not fields.get('State'):
        raise ReleaseError('Unrecognized buildinfo response for {}: {}'.format(nvr, result.stdout))
    task = re.match(r'\d+', fields.get('Task', ''))
    return {'state': fields['State'], 'tags': fields.get('Tags', '').split(),
            'task': task.group() if task else None, 'source': fields.get('Source')}


def rpm_identity(spec, target):
    """Query name and NVR with one consistent macro context."""
    try:
        value, _ = specfile_macro_lookup(str(spec), '%{name}\n%{nvr}', scl=target.get('scl'),
                                         dist=target['dist'], macros=target['macros'])
    except subprocess.CalledProcessError as error:
        raise ReleaseError('Cannot query {}: {}'.format(spec, error.stderr or error.stdout)) from error
    name, nvr = value.strip().splitlines()
    return name, nvr


def macro_arguments(target):
    """Build the macro options shared by source expansion and scratch SRPMs."""
    macros = dict(target['macros'], dist=target['dist'])
    if target.get('scl'):
        macros['scl'] = target['scl']
    return [part for key, value in macros.items() for part in ('--define', '{} {}'.format(key, value))]


def spec_inputs(spec, target):
    """List source and patch filenames using the destination macro context."""
    output = run(['spectool', '--list-files', '--all'] + macro_arguments(target) + [str(spec)]).stdout
    for kind, value in re.findall(r'^(Source\d*|Patch\d*):\s*(.+)$', output, re.MULTILINE):
        filename = os.path.basename(urlsplit(value).path)
        if not filename or filename in ('.', '..'):
            raise ReleaseError('Invalid spec input {}'.format(value))
        yield kind, filename


class RhpkgRelease:  # pylint: disable=too-many-instance-attributes
    """Submit independent build targets before waiting and tagging their results."""

    # Preserve dist-git service configuration when replacing packaging inputs.
    protected = {'Makefile', 'branch', 'sources', 'package.cfg', 'gating.yaml', 'tests', 'plans'}

    def __init__(self, options):
        self.options = options
        self.directory = Path(options['directory']).resolve()
        self.spec = Path(options['spec_file']).resolve()
        self.brew = options['koji_executable']
        self.rhpkg = options['rhpkg_executable']
        self.targets = normalize_targets(options['targets'], self.directory.name)
        self.receipt = Path(options['receipt'])
        self.previous = {}
        if self.receipt.exists():
            self.previous = json.loads(self.receipt.read_text()).get('targets', {})
        self.results = []
        self.errors = []
        self.changed = False

    def save(self):
        """Persist submitted tasks so a later invocation can finish tagging."""
        if self.options.get('check_mode'):
            return
        self.receipt.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', dir=self.receipt.parent, delete=False) as stream:
            targets = dict(self.previous)
            for item in self.results:
                previous = targets.get(item['target']['name'], {})
                # A failed query or resume validation must not discard a pending task.
                if item.get('processed') and (item['tasks'] or not previous.get('tasks') or
                                             previous.get('state') == 'COMPLETE' or item['state'] == 'COMPLETE'):
                    targets[item['target']['name']] = item
            json.dump({'targets': targets}, stream, indent=2)
            temporary = stream.name
        os.replace(temporary, self.receipt)

    def execute(self):
        """Return all successes and failures, including recoverable pending tags."""
        identities = set()
        for target in self.targets:
            name, nvr = rpm_identity(self.spec, target)
            if nvr in identities:
                raise ReleaseError('Multiple build targets produce {}; combine their output tags'.format(nvr))
            identities.add(nvr)
            self.results.append({'target': target, 'package': name, 'nvr': nvr, 'tasks': [],
                                 'task_urls': [], 'source_sha': None,
                                 'pending_tags': [] if self.options['scratch'] else target['tags'],
                                 'state': 'PENDING', 'changed': False})
        for item in self.results:
            try:
                self.submit(item)
            except (ReleaseError, OSError, ValueError) as error:
                item['state'] = 'FAILED'
                self.errors.append('{}: {}'.format(item['target']['name'], error))
            item['processed'] = True
            self.save()
        for item in self.results:
            if item['state'] == 'FAILED':
                continue
            try:
                self.finish(item)
            except (ReleaseError, OSError, ValueError) as error:
                item['state'] = 'FAILED'
                self.errors.append('{}: {}'.format(item['target']['name'], error))
            self.save()
        return {'changed': self.changed, 'results': self.results, 'errors': self.errors,
                'pending': any(item['state'] == 'PENDING' for item in self.results)}

    def submit(self, item):
        """Reuse complete/in-flight builds, otherwise prepare and submit dist-git."""
        target = item['target']
        if not self.options['scratch']:
            info = build_info(self.brew, item['nvr'])
            resumed = self.resume(item)
            if info['state'] == 'COMPLETE':
                item['state'] = 'COMPLETE'
                return
            if info['state'] == 'BUILDING' and info['task']:
                item['tasks'] = [info['task']]
                return
            if info['state'] != 'MISSING':
                raise ReleaseError('{} is {}; refusing another submission'.format(item['nvr'], info['state']))
            if resumed:
                return
        elif self.resume(item):
            return
        if self.options.get('check_mode'):
            item['changed'] = self.changed = True
            return
        output = run([self.brew, 'list-targets', '--quiet', '--name', target['build_target']]).stdout
        if not any(line.split() and line.split()[0] == target['build_target'] for line in output.splitlines()):
            raise ReleaseError('Unknown build target {}'.format(target['build_target']))
        self.check_registration(item, target['tags'])
        item['input_digest'] = self.input_digest(target)
        if self.options['scratch']:
            self.scratch_build(item)
        else:
            self.prepare_and_build(item)

    def check_registration(self, item, tags):
        """Validate destination eligibility before a release submission or tag operation."""
        if not self.options['tag_check'] or self.options['scratch'] or self.options.get('check_mode'):
            return
        for tag in tags:
            try:
                registered = package_whitelisted(self.brew, tag, item['package'])
            except KojiCommandError as error:
                raise ReleaseError('Unable to check package registration: {}'.format(error.message)) from error
            if not registered:
                raise ReleaseError('{} is not registered or is blocked in {}'.format(item['package'], tag))

    def resume(self, item):
        """Recover tasks that may not have reserved a build record yet."""
        previous = self.previous.get(item['target']['name'], {})
        if not previous.get('tasks') or previous.get('state') == 'COMPLETE':
            return False
        if previous['nvr'] != item['nvr'] or previous['target'] != item['target']:
            # Scratch tasks do not reserve NVRs, so buildinfo cannot establish
            # whether an earlier scratch task has finished.
            if not self.options['scratch']:
                old = build_info(self.brew, previous['nvr'])
                if old['state'] in ('COMPLETE', 'FAILED', 'CANCELED', 'DELETED'):
                    return False
            raise ReleaseError('An earlier task is pending for a different release; finish it first')
        if not self.options.get('check_mode') and previous.get('input_digest') != self.input_digest(item['target']):
            raise ReleaseError('Package sources changed while a release task was pending; finish it first')
        item.update({key: previous.get(key) for key in ('tasks', 'task_urls', 'source_sha', 'input_digest')})
        return True

    def input_digest(self, target):
        """Bind pending tasks to the exact spec and source bytes requested."""
        digest = hashlib.sha256(self.spec.read_bytes())
        for filename, (source, _) in sorted(self.source_files(target).items()):
            digest.update(filename.encode())
            with source.open('rb') as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
        return digest.hexdigest()

    def source_files(self, target):
        """Resolve spec inputs without copying annex links into dist-git."""
        files = {}
        for kind, filename in spec_inputs(self.spec, target):
            if filename.startswith('.') or filename in self.protected:
                raise ReleaseError('Spec input conflicts with dist-git configuration: {}'.format(filename))
            source = self.directory / filename
            if not source.is_file():
                run(['git', 'annex', 'get', '--', filename], self.directory)
            if not source.is_file():
                raise ReleaseError('Missing source {}'.format(source))
            tracked = kind.startswith('Patch') or filename.endswith(('.patch', '.changes', '.rpmlintrc'))
            files[filename] = (source, tracked)
        return files

    def sync(self, checkout, target):
        """Replace packaging inputs while preserving dist-git service files."""
        files = self.source_files(target)
        files[self.spec.name] = (self.spec, True)
        previous_inputs = set()
        for spec in checkout.glob('*.spec'):
            previous_inputs.add(spec.name)
            previous_inputs.update(filename for _, filename in spec_inputs(spec, target))
        tracked = run(['git', 'ls-files', '-z'], checkout).stdout.split('\0')
        for filename in tracked:
            if filename in previous_inputs and not filename.startswith('.') and filename not in self.protected:
                if filename not in files:
                    run(['git', 'rm', '--', filename], checkout)
        for filename, (source, _) in files.items():
            destination = checkout / filename
            if destination.is_symlink():
                destination.unlink()
            shutil.copyfile(source, destination)
        return files

    def prepare_and_build(self, item):
        """Submit a normal release from dist-git through rhpkg."""
        target = item['target']
        with tempfile.TemporaryDirectory(prefix='obal-rhpkg-') as temporary:
            checkout = Path(temporary) / 'distgit'
            run([self.rhpkg, 'clone', '--branch', target['distgit_branch'], target['distgit_package'], str(checkout)])
            files = self.sync(checkout, target)
            command = [self.rhpkg, '--release', target['distgit_branch'], 'build', '--nowait',
                       '--target', target['build_target']]
            self.commit(checkout, files, item)
            item['source_sha'] = run(['git', 'rev-parse', 'HEAD'], checkout).stdout.strip()
            command.append('--skip-nvr-check')
            result = run(command, checkout, check=False)
            if result.returncode:
                # A concurrent release can win the NVR race after our initial query.
                if 'already been built' in result.stdout:
                    info = build_info(self.brew, item['nvr'])
                    if info['state'] == 'COMPLETE':
                        item['source_sha'] = None
                        item['state'] = 'COMPLETE'
                        return
                raise ReleaseError('rhpkg build failed: {}'.format(result.stdout))
            self.record_submission(item, result.stdout)

    def scratch_build(self, item):
        """Build an SRPM from local/annex sources and submit it directly to Koji."""
        target = item['target']
        with tempfile.TemporaryDirectory(prefix='obal-scratch-') as temporary:
            directory = Path(temporary)
            sources = directory / 'SOURCES'
            sources.mkdir()
            for filename, (source, _) in self.source_files(target).items():
                shutil.copyfile(source, sources / filename)
            spec = directory / self.spec.name
            shutil.copyfile(self.spec, spec)
            output = run(['rpmbuild', '-bs', str(spec), '--define', '_topdir ' + temporary,
                          '--define', '_sourcedir ' + str(sources), '--define', '_srcrpmdir ' + temporary] +
                         macro_arguments(target), directory).stdout
            matches = re.findall(r'^Wrote:\s*(.*\.src\.rpm)\s*$', output, re.MULTILINE)
            if not matches:
                raise ReleaseError('rpmbuild returned no source RPM: {}'.format(output))
            srpm = str((directory / matches[-1]).resolve())
            result = run([self.brew, 'build', '--scratch', '--nowait', target['build_target'], srpm])
            self.record_submission(item, result.stdout)

    def record_submission(self, item, output):
        """Capture Koji task identifiers from either submission client."""
        item['tasks'] = re.findall(r'^Created task:\s*(\d+)', output, re.MULTILINE)
        item['task_urls'] = re.findall(r'^Task info:\s*(.+)', output, re.MULTILINE)
        if not item['tasks']:
            raise ReleaseError('Build submission returned no task ID: {}'.format(output))
        item['changed'] = self.changed = True

    def commit(self, checkout, files, item):
        """Upload sources and push an actual packaging change before building."""
        uploads = sorted(filename for filename, (_, tracked) in files.items() if not tracked)
        if uploads:
            run([self.rhpkg, 'new-sources'] + uploads, checkout)
            tracked_sources = set(run(['git', 'ls-files', '-z'], checkout).stdout.split('\0'))
            for filename in uploads:
                if filename in tracked_sources:
                    run(['git', 'rm', '--cached', '--', filename], checkout)
        elif (checkout / 'sources').exists():
            (checkout / 'sources').write_text('')
        tracked = sorted(filename for filename, (_, keep) in files.items() if keep)
        for filename in ('sources', '.gitignore'):
            if (checkout / filename).is_file():
                tracked.append(filename)
        run(['git', 'add', '--'] + tracked, checkout)
        difference = run(['git', 'diff', '--cached', '--quiet'], checkout, check=False)
        if difference.returncode not in (0, 1):
            raise ReleaseError(difference.stdout)
        if difference.returncode:
            for field in ('user.name', 'user.email'):
                value = run(['git', 'config', field], self.directory).stdout.strip()
                run(['git', 'config', field, value], checkout)
            run([self.rhpkg, 'commit', '-m', 'Update {}'.format(item['nvr'])], checkout)
            item['changed'] = self.changed = True
            run([self.rhpkg, 'push'], checkout)

    def finish(self, item):
        """Wait for builds, then wait for and verify every requested output tag."""
        if self.options.get('check_mode'):
            info = build_info(self.brew, item['nvr'])
            missing = set(item['target']['tags']) - set(info['tags'])
            item['changed'] = info['state'] != 'COMPLETE' or bool(missing)
            self.changed |= item['changed']
            return
        if item['tasks'] and item['state'] != 'COMPLETE':
            if not self.options['wait']:
                return
            for task in item['tasks']:
                watched = run([self.brew, 'watch-task', task], check=False)
                if self.options['download_logs']:
                    run([self.brew, 'download-logs', '-r', task], self.options['output_directory'])
                if watched.returncode:
                    raise ReleaseError('Build task {} failed: {}'.format(task, watched.stdout))
        if not self.options['scratch']:
            self.reconcile(item)
        else:
            item['pending_tags'] = []
        if self.options['download_rpms']:
            self.download(item)
        item['state'] = 'COMPLETE'

    def download(self, item):
        """Download completed results, including builds reused by tagging only."""
        destination = Path(self.options['output_directory']) / 'downloaded_rpms' / item['target']['name']
        destination.mkdir(parents=True, exist_ok=True)
        if self.options['scratch']:
            for task in item['tasks']:
                run([self.brew, 'download-task', '--arch=noarch', '--arch=x86_64', task], destination)
        else:
            run([self.brew, 'download-build', item['nvr']], destination)

    def reconcile(self, item):
        """A complete build must have the expected identity before it can be tagged."""
        info = build_info(self.brew, item['nvr'])
        if info['state'] != 'COMPLETE':
            raise ReleaseError('Expected complete build {}; found {}'.format(item['nvr'], info['state']))
        if item['source_sha'] and (not info['source'] or not info['source'].endswith('#' + item['source_sha'])):
            raise ReleaseError('Build source does not match the submitted dist-git commit for {}'.format(item['nvr']))
        self.check_registration(item, [tag for tag in item['target']['tags'] if tag not in info['tags']])
        for tag in item['target']['tags']:
            if tag not in info['tags']:
                result = run([self.brew, 'tag-build', '--wait', tag, item['nvr']], check=False)
                info = build_info(self.brew, item['nvr'])
                if tag not in info['tags']:
                    raise ReleaseError('Unable to tag {} into {}: {}'.format(item['nvr'], tag, result.stdout))
                item['changed'] = self.changed = True
            item['pending_tags'] = [name for name in item['target']['tags'] if name not in info['tags']]
            self.save()
        if self.options['waitrepo']:
            run([self.brew, 'wait-repo', '--build=' + item['nvr'], '--target', item['target']['build_target']])
