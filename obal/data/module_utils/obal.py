"""
Ansible module helper functions for obal modules
"""
import subprocess


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
    return evr.split("\n")[0].split(" ")[-1]


def get_specfile_evr(specfile):
    """get the EVR from the source header of the specfile"""
    return specfile_macro_lookup(specfile, '%{evr}')


def get_specfile_name(specfile, scl=None):
    """get the name from the specfile"""
    return specfile_macro_lookup(specfile, '%{name}', scl=scl)


def get_specfile_nevr(specfile, scl=None, dist=None, macros=None):
    """get the name from the specfile"""
    return specfile_macro_lookup(specfile, '%{nevr}', scl=scl, dist=dist, macros=macros)


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
