"""
Build SRPM
"""

import shutil
import os
import subprocess
from contextlib import contextmanager
from tempfile import mkdtemp

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


def run_command(command):
    """
    Run a system command
    """
    return subprocess.check_output(
        command,
        universal_newlines=True,
        stderr=subprocess.STDOUT
    )


def copy_sources(spec_file, package_dir, sources_dir):
    """
    Copy RPM sources to rpmbuild environment
    """
    command = ["spectool", "--list-files", spec_file]
    sources = run_command(command)

    for source in sources.split("\n"):
        if not source:
            continue

        source_link = source.split(' ')[1]

        if not source_link.startswith('http'):
            shutil.copy(os.path.join(package_dir, source_link), sources_dir)

    with chdir(package_dir):
        run_command(["git-annex", "lock"])
        annexed_files = run_command(["git-annex", "find", "--include", "*"])
        annexed_files = annexed_files.splitlines()

        if not annexed_files:
            return

        run_command(["git-annex", "get"])

        try:
            run_command(["git-annex", "unlock"])
        finally:
            for annex in annexed_files:
                shutil.copy(annex, sources_dir)

            run_command(["git-annex", "lock", "--force"])


def main():
    """
    Build a package using tito
    """
    module = AnsibleModule(
        argument_spec=dict(
            package=dict(type='str', required=False),
            scl=dict(type='str', required=False),
            output=dict(type='path', required=False),
        )
    )

    package = module.params['package']
    output = module.params['output']
    scl = module.params['scl']

    spec_file = os.path.join(package, '%s.spec' % os.path.basename(package))

    try:
        base_dir = mkdtemp()
        sources_dir = os.path.join(base_dir, 'SOURCES')
        build_dir = os.path.join(base_dir, 'BUILD')

        os.mkdir(sources_dir)
        os.mkdir(build_dir)

        copy_sources(spec_file, package, sources_dir)
        shutil.copy(spec_file, base_dir)

        command = ['rpmbuild', '-bs']
        command += ['--define', '_topdir %s' % base_dir]
        command += ['--define', '_sourcedir %s' % sources_dir]
        command += ['--define', '_builddir %s' % build_dir]
        command += ['--define', '_srcrpmdir %s' % base_dir]
        command += ['--define', '_rpmdir %s' % base_dir]
        command += ['--undefine', 'dist']

        if scl:
            command += ['--define', 'scl %s' %  scl]

        command += [os.path.join(base_dir, '%s.spec' % os.path.basename(package))]

        try:
            result = run_command(command)
        except subprocess.CalledProcessError as error:
            module.fail_json(msg='Failed to srpm build', command=' '.join(command), output=error.output)

        result = result.split("Wrote: ")[-1].rstrip()

        if not os.path.exists(output):
            os.mkdir(output)

        shutil.copy(result, output)
        path = os.path.join(output, os.path.basename(result))

        module.exit_json(changed=True, path=path)
    except subprocess.CalledProcessError as error:
        module.fail_json(msg='Failed to build srpm', output=error.output)
    finally:
        shutil.rmtree(base_dir)


if __name__ == '__main__':
    main()
