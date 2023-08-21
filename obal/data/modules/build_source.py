"""
Build a source package
"""

import os
import re
from contextlib import contextmanager
from glob import glob
from subprocess import CalledProcessError, check_output

from ansible.module_utils.basic import AnsibleModule


@contextmanager
def chdir(directory):
    """
    Change the directory in a context manager. Automatically switches back even if an exception
    occurs.
    """
    old = os.getcwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(old)


def main():
    """
    Build a source package
    """
    module = AnsibleModule(
        argument_spec=dict(
            directory=dict(required=True),
        )
    )

    directory = module.params['directory']
    path = None

    with chdir(directory):
        if os.path.exists(os.path.join(directory, 'Rakefile.dist')):
            try:
                output = check_output(['rake', '-f', 'Rakefile.dist', 'pkg:generate_source'],
                                      universal_newlines=True).rstrip()
            except CalledProcessError as error:
                module.fail_json(msg='Failed to build using Rakefile.dist',
                                 stdout=error.stdout, stderr=error.stderr)
            if not output:
                module.fail_json(msg='Failed to determine the output file')
            path = output.splitlines()[-1]
        elif glob(os.path.join(directory, '*.gemspec')):
            gemspecs = glob(os.path.join(directory, '*.gemspec'))
            if len(gemspecs) != 1:
                gemspec = os.path.join(directory, os.path.basename(directory) + '.gemspec')
                if gemspec not in gemspecs:
                    module.fail_json(msg='Multiple gemspecs found', gemspecs=gemspecs)
            else:
                gemspec = gemspecs[0]

            try:
                # TODO: use --output to set the path?
                output = check_output(['gem', 'build', gemspec], universal_newlines=True)
            except CalledProcessError as error:
                module.fail_json(msg='Failed to build gemspec', gemspec=gemspec,
                                 stdout=error.stdout, stderr=error.stderr)

            match = re.search(r'File: (?P<path>.+\.gem)', output)
            if not match:
                module.fail_json(msg='Failed to determine gem file from output', output=output,
                                 gemspec=gemspec)
            path = match.group('path')
        elif os.path.exists('Rakefile'):
            # TODO: bundle install?
            try:
                output = check_output(['bundle', 'exec', 'rake', 'pkg:generate_source'],
                                      universal_newlines=True).rstrip()
            except CalledProcessError as error:
                module.fail_json(msg='Failed to build using Rakefile.dist',
                                 stdout=error.stdout, stderr=error.stderr)
            if not output:
                module.fail_json(msg='Failed to determine the output file')
            path = output.splitlines()[-1]
        else:
            module.fail_json(msg='Unsupported package directory')

    if not os.path.isabs(path):
        path = os.path.join(directory, path)

    if not os.path.exists(path):
        module.fail_json(msg="Determined path doesn't exist", path=path)

    module.exit_json(changed=path is not None, path=path)


if __name__ == '__main__':
    main()
