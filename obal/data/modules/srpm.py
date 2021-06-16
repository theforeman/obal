"""
Build SRPM
"""

import shutil
import os
import subprocess
from zipfile import ZipFile
from contextlib import contextmanager
from tempfile import mkdtemp, TemporaryFile

from ansible.module_utils.six.moves.urllib.request import urlopen # pylint:disable=import-error,no-name-in-module
from ansible.module_utils.six.moves.urllib.error import HTTPError # pylint:disable=import-error,no-name-in-module

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.obal import run_command, get_specfile_sources # pylint:disable=import-error,no-name-in-module


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


def copy_sources(spec_file, package_dir, sources_dir):
    """
    Copy RPM sources to rpmbuild environment
    """
    sources = get_specfile_sources(spec_file)

    for source in sources:
        if not source.startswith('http'):
            shutil.copy(os.path.join(package_dir, source), sources_dir)

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


def fetch_remote_sources(source_location, source_system, sources_dir):
    """
    Copy RPM sources from a remote source like Jenkins to rpmbuild environment
    """
    source_system_urls = {
        'jenkins': '{}/lastSuccessfulBuild/artifact/*zip*/archive.zip',
    }

    url = source_system_urls[source_system].format(source_location)
    request = urlopen(url)

    with TemporaryFile() as archive:
        archive.write(request.read())

        with ZipFile(archive) as zip_file:
            for zip_info in zip_file.infolist():
                if zip_info.filename[-1] == '/':
                    continue

                zip_info.filename = os.path.basename(zip_info.filename)
                zip_file.extract(zip_info, sources_dir)


def main():
    """
    Build a package using tito
    """
    module = AnsibleModule(
        argument_spec=dict(
            package=dict(type='str', required=False),
            scl=dict(type='str', required=False),
            output=dict(type='path', required=False),
            source_location=dict(type='str', required=False),
            source_system=dict(type='str', required=False),
        )
    )

    package = module.params['package']
    output = module.params['output']
    scl = module.params['scl']
    source_location = module.params['source_location']
    source_system = module.params['source_system']

    spec_file = os.path.join(package, '%s.spec' % os.path.basename(package))

    try:
        base_dir = mkdtemp()
        sources_dir = os.path.join(base_dir, 'SOURCES')
        build_dir = os.path.join(base_dir, 'BUILD')

        os.mkdir(sources_dir)
        os.mkdir(build_dir)

        if source_location:
            try:
                fetch_remote_sources(source_location, source_system, sources_dir)
            except HTTPError as error:
                module.fail_json(msg="HTTP %s: %s. Check %s exists." % (error.code, error.reason, source_location))
            except KeyError as error:
                module.fail_json(msg="Unknown source_system specified.", output=error)

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
