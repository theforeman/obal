#!/usr/bin/env python3
"""Stateful Brew/rhpkg test clients; all dist-git operations use local Git."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


state_path = Path(os.environ['OBAL_BREW_STATE'])
state = json.loads(state_path.read_text())
program = Path(sys.argv[0]).name
arguments = sys.argv[1:]
state['commands'].append([program] + arguments)
state_path.write_text(json.dumps(state))


def execute(command, cwd=None):
    return subprocess.check_output(command, cwd=cwd, text=True, stderr=subprocess.STDOUT).strip()


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def build_info(nvr):
    if state.get('query_error'):
        fail('Authentication failed')
    build = state['builds'].get(nvr)
    if not build:
        fail('No such build: ' + nvr)
    print('BUILD: {} [1]'.format(nvr))
    print('State: ' + build['state'])
    print('Task: ' + str(build.get('task', 'none')))
    print('Source: ' + build.get('source', 'git://example.test/rpms/package#original'))
    print('Tags: ' + ' '.join(build.get('tags', [])))


def brew():
    command = arguments[0]
    if command == 'buildinfo':
        build_info(arguments[1])
    elif command == 'list-targets':
        target = arguments[-1]
        if target in state['targets']:
            print('{} {}-build {}'.format(target, target, target))
    elif command == 'list-pkgs':
        if state.get('registration_error'):
            fail('Authentication failed while querying package registration')
        tag = arguments[arguments.index('--tag') + 1]
        packages = ([arguments[arguments.index('--package') + 1]] if '--package' in arguments
                    else sorted(state['repositories']))
        if state.get('unregistered') or tag in state.get('unregistered_tags', []):
            fail('(no matching packages)')
        if tag not in state.get('blocked_tags', []):
            for package in packages:
                print(package + ' ' + tag + ' test-owner')
    elif command == 'build':
        assert arguments[1:3] == ['--scratch', '--nowait']
        target, srpm = arguments[3:]
        if target in state.get('submission_errors', []):
            fail('Submission rejected')
        assert Path(srpm).is_file()
        nvr = execute(['rpmquery', '--queryformat', '%{nvr}', '--package', srpm])
        assert nvr.endswith(state['targets'][target]['dist'])
        archive = subprocess.check_output(['rpm2cpio', srpm])
        payload = subprocess.check_output(['cpio', '-i', '--to-stdout', 'payload.txt'],
                                          input=archive, stderr=subprocess.PIPE)
        task_id = str(1000 + len(state['tasks']))
        state['tasks'][task_id] = dict(nvr=nvr, source=srpm, target=target, scratch=True, state='open',
                                       source_sha256=hashlib.sha256(payload).hexdigest())
        print('Created task: ' + task_id)
        print('Task info: https://brew.example.test/taskinfo?taskID=' + task_id)
    elif command == 'watch-task':
        task = state['tasks'][arguments[1]]
        if task['target'] in state.get('failed_targets', []):
            fail('Build failed')
        task['state'] = 'closed'
        if not task['scratch']:
            state['builds'][task['nvr']] = dict(state='COMPLETE', task=arguments[1],
                                               source=task['source'], tags=[task['target']])
    elif command == 'tag-build':
        assert arguments[1] == '--wait'
        tag, nvr = arguments[-2:]
        if tag in state.get('failed_tags', []):
            fail('Tag permission denied')
        state['builds'][nvr]['tags'].append(tag)
        print('Created task 9000')
    elif command in ('wait-repo', 'download-logs', 'download-task', 'download-build'):
        pass
    else:
        fail('Unexpected Brew command: ' + command)


def rhpkg():
    args = arguments[:]
    if args[0] == '--release':
        args = args[2:]
    command = args[0]
    if command == 'clone':
        assert args[1] == '--branch'
        branch, package, destination = args[2:]
        execute(['git', 'clone', '--branch', branch, state['repositories'][package], destination])
    elif command == 'new-sources':
        lines = []
        for filename in args[1:]:
            digest = hashlib.sha512(Path(filename).read_bytes()).hexdigest()
            lines.append('SHA512 ({}) = {}'.format(filename, digest))
        Path('sources').write_text('\n'.join(lines) + '\n')
        Path('.gitignore').write_text('\n'.join(args[1:]) + '\n')
    elif command == 'commit':
        execute(['git', 'commit'] + args[1:])
    elif command == 'push':
        if state.get('push_error'):
            fail('Push rejected')
        execute(['git', 'push', 'origin', 'HEAD'])
    elif command == 'build':
        assert '--scratch' not in args
        assert '--srpm' not in args
        target = args[args.index('--target') + 1]
        if target in state.get('submission_errors', []):
            fail('Submission rejected')
        context = state['targets'][target]
        spec = next(Path('.').glob('*.spec'))
        query = ['rpmspec', '--query', '--srpm', '--queryformat', '%{nvr}', str(spec)]
        for name, value in context.items():
            query += ['--define', '{} {}'.format(name, value)]
        nvr = execute(query)
        assert execute(['git', 'rev-parse', 'HEAD']) == execute(['git', 'rev-parse', '@{upstream}'])
        task_id = str(1000 + len(state['tasks']))
        source = 'git://example.test/rpms/package#' + execute(['git', 'rev-parse', 'HEAD'])
        task = dict(nvr=nvr, source=source, target=target, scratch=False, state='open')
        state['tasks'][task_id] = task
        if not state.get('delay_build_record'):
            state['builds'][nvr] = dict(state='BUILDING', task=task_id, source=source, tags=[])
        print('Created task: ' + task_id)
        print('Task info: https://brew.example.test/taskinfo?taskID=' + task_id)
    else:
        fail('Unexpected rhpkg command: ' + command)


if program in ('brew', 'koji'):
    brew()
elif program == 'rhpkg':
    rhpkg()
else:
    fail('Unexpected client: ' + program)
state_path.write_text(json.dumps(state))
