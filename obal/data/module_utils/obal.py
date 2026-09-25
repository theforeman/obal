"""
Ansible module helper functions for obal modules
"""
import subprocess
import os

try:
    from ansible.module_utils.koji_wrapper import koji, KojiCommandError # pylint:disable=import-error,no-name-in-module
except ImportError:
    # when trying to import this file outside the ansible context, we cannot rely on the magic ansible import path
    from .koji_wrapper import koji, KojiCommandError # pylint:disable=import-error,no-name-in-module


def macro_lookup(command, scl=None, dist=None, macros=None):
    """run a macro lookup command, returning stdout and stderr separately"""
    if dist:
        command += ['--define', 'dist %s' % dist]
    else:
        command += ['--undefine', 'dist']

    if scl:
        command += ['--define', 'scl %s' % scl]

    if macros is not None:
        for (macro, value) in macros.items():
            command += ['--define', '%s %s' % (macro, value)]

    result = subprocess.run(
        command,
        capture_output=True,
        universal_newlines=True,
        check=True,
    )
    return result.stdout, result.stderr


def specfile_macro_lookup(specfile, macro_str, scl=None, dist=None, macros=None):
    """expand a given macro from a specfile, returning value and stderr"""
    command = [
        'rpmspec',
        '--query',
        '--queryformat',
        macro_str,
        '--srpm',
        specfile
    ]

    return macro_lookup(command, scl=scl, dist=dist, macros=macros)


def srpm_macro_lookup(srpm, macro_str, scl=None, dist=None, macros=None):
    """expand a given macro from an srpm, returning value and stderr"""
    command = [
        'rpmquery',
        '--queryformat',
        macro_str,
        '--package',
        srpm
    ]

    return macro_lookup(command, scl=scl, dist=dist, macros=macros)


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
    value, _stderr = specfile_macro_lookup(specfile, '%{evr}')
    return value


def get_srpm_evr(srpm):
    """get the EVR from the source header of the srpm"""
    value, _stderr = srpm_macro_lookup(srpm, '%{evr}')
    return value


def get_specfile_name(specfile, scl=None):
    """get the name from the specfile"""
    value, _stderr = specfile_macro_lookup(specfile, '%{name}', scl=scl)
    return value


def get_srpm_name(srpm, scl=None):
    """get the name from the srpm"""
    value, _stderr = srpm_macro_lookup(srpm, '%{name}', scl=scl)
    return value


def get_specfile_nevr(specfile, scl=None, dist=None, macros=None):
    """get the name, epoch, version and release from the specfile"""
    value, _stderr = specfile_macro_lookup(specfile, '%{nevr}', scl=scl, dist=dist, macros=macros)
    return value


def get_srpm_nevr(srpm, scl=None, dist=None, macros=None):
    """get the name, epoch, version and release from the srpm"""
    value, _stderr = srpm_macro_lookup(srpm, '%{nevr}', scl=scl, dist=dist, macros=macros)
    return value


def get_specfile_nvr(specfile, scl=None, dist=None, macros=None):
    """get the name, version and release from the specfile"""
    value, _stderr = specfile_macro_lookup(specfile, '%{nvr}', scl=scl, dist=dist, macros=macros)
    return value


def get_srpm_nvr(srpm, scl=None, dist=None, macros=None):
    """get the name, version and release from the srpm"""
    value, _stderr = srpm_macro_lookup(srpm, '%{nvr}', scl=scl, dist=dist, macros=macros)
    return value


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
    sources = run_command(["spectool", "--list-files", "--all", specfile])
    return [source.split(' ')[1] for source in sources.split("\n")
            if source and (source.startswith('Source') or source.startswith('Patch'))]


def run_command(command):
    """
    Run a system command
    """
    env = dict(os.environ, LANG="C.utf8")

    return subprocess.check_output(
        command,
        universal_newlines=True,
        stderr=subprocess.STDOUT,
        env=env
    )
