"""
Ansible module helper functions for obal modules
"""
import subprocess

try:
    from ansible.module_utils.koji_wrapper import koji, KojiCommandError # pylint:disable=import-error,no-name-in-module
except ImportError:
    # when trying to import this file outside the ansible context, we cannot rely on the magic ansible import path
    from .koji_wrapper import koji, KojiCommandError # pylint:disable=import-error,no-name-in-module


def specfile_macro_lookup(specfile, macro_str, scl=None, dist=None, macros=None):
    """expand a given macro from a specfile"""
    command = [
        'rpmspec',
        '--query',
        '--queryformat',
        macro_str,
        '--srpm',
        specfile
    ]

    if dist:
        command += ['--define', '"dist %s"' % dist]
    else:
        command += ['--undefine', 'dist']

    if scl:
        command += ['--define', '"scl %s"' % scl]

    if macros is not None:
        for (macro, value) in macros.items():
            command += ['--define', '"%s %s"' % (macro, value)]

    return subprocess.check_output(' '.join(command), universal_newlines=True, shell=True)


def get_changelog_evr(specfile):
    """get the EVR from the last changelog entry in the specfile"""
    cmd = [
        'rpm',
        '--query',
        '--changelog',
        '--specfile',
        specfile
    ]
    evr = subprocess.check_output(cmd, universal_newlines=True)
    return evr.splitlines()[0].split(" ")[-1]


def get_specfile_evr(specfile):
    """get the EVR from the source header of the specfile"""
    return specfile_macro_lookup(specfile, '%{evr}')


def get_specfile_name(specfile, scl=None):
    """get the name from the specfile"""
    return specfile_macro_lookup(specfile, '%{name}', scl=scl)


def get_specfile_nevr(specfile, scl=None, dist=None, macros=None):
    """get the name, epoch, version and release from the specfile"""
    return specfile_macro_lookup(specfile, '%{nevr}', scl=scl, dist=dist, macros=macros)


def get_specfile_nvr(specfile, scl=None, dist=None, macros=None):
    """get the name, version and release from the specfile"""
    return specfile_macro_lookup(specfile, '%{nvr}', scl=scl, dist=dist, macros=macros)


def get_whitelist_status(build_command, tag, package):
    """
    Get whitelist status of a given package within a tag.

    Return `True` if the package is whitelisted, `False` otherwise.
    """
    cmd = [
        'list-pkgs',
        '--tag',
        tag,
        '--package',
        package,
        '--quiet'
    ]

    try:
        koji(cmd, build_command)
        return True
    except KojiCommandError:
        return False


def get_specfile_sources(specfile):
    """
    Get a list of sources and patches from a specfile

    Returns the filenames or URLs as an array
    """
    sources = run_command(["spectool", "--list-files", specfile])
    return [source.split(' ')[1] for source in sources.split("\n")
            if source and (source.startswith('Source') or source.startswith('Patch'))]


def run_command(command):
    """
    Run a system command
    """
    return subprocess.check_output(
        command,
        universal_newlines=True,
        stderr=subprocess.STDOUT
    )
