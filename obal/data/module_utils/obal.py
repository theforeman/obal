"""
Ansible module helper functions for obal modules
"""
import subprocess


def specfile_macro_lookup(specfile, macro_str):
    """expand a given macro from a specfile"""
    cmd = [
        'rpmspec',
        '--query',
        '--queryformat',
        macro_str,
        '--undefine',
        'dist',
        '--undefine',
        'foremandist',
        '--srpm',
        specfile
    ]
    return subprocess.check_output(cmd)


def get_changelog_evr(specfile):
    """get the EVR from the last changelog entry in the specfile"""
    cmd = [
        'rpm',
        '--query',
        '--changelog',
        '--specfile',
        specfile
    ]
    evr = subprocess.check_output(cmd)
    return evr.split("\n")[0].split(" ")[-1]


def get_specfile_evr(specfile):
    """get the EVR from the source header of the specfile"""
    return specfile_macro_lookup(specfile, '%{evr}')


def get_specfile_name(specfile):
    """get the name from the specfile"""
    return specfile_macro_lookup(specfile, '%{name}')


def get_whitelist_status(build_command, tag, package):
    """
    Get whitelist status of a given package within a tag.

    Return `True` if the package is whitelisted, `False` otherwise.
    """
    cmd = [
        build_command,
        'list-pkgs',
        '--tag',
        tag,
        '--package',
        package,
        '--quiet'
    ]
    retcode = subprocess.call(cmd)
    return retcode == 0
