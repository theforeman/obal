#!/usr/bin/env python2
# PYTHON_ARGCOMPLETE_OK

"""
Obal is a wrapper around Ansible playbooks. They are exposed as a command line application.
"""

from __future__ import print_function

import argparse
import glob
import os
import sys

from pkg_resources import resource_filename

try:
    import argcomplete
except ImportError:
    argcomplete = None


# Need for PlaybookCLI to set the verbosity
display = None  # pylint: disable=C0103


class Playbook(object):  # pylint: disable=R0903
    """
    An abstraction over an Ansible playbook
    """
    def __init__(self, path):
        self.path = path

        filename = os.path.basename(path)
        self.name = os.path.splitext(filename)[0]

    @property
    def takes_package_parameter(self):
        """
        Whether this playbook takes a package argument.

        This is determined by a hosts: packages inside the playbook
        """
        # TODO: Read this from the playbook itself?
        return self.name != 'setup'

    def __str__(self):
        return self.name

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, self.path)


def find_playbooks(playbooks_path):
    """
    Find all playbooks in the given path.
    """
    paths = glob.glob(os.path.join(playbooks_path, '*.yml'))
    return [Playbook(playbook_path) for playbook_path in paths]


def _get_data_path():
    """
    Return the data path. Houses playbooks and configs.
    """
    return resource_filename(__name__, 'data')


def get_playbooks_path():
    """
    Return the default playbooks path
    """
    return os.path.join(_get_data_path(), 'playbooks')


def get_ansible_config_path():
    """
    Return the default playbooks path
    """
    return os.path.join(_get_data_path(), 'ansible.cfg')


def find_packages(inventory_path):
    """
    Find all packages in the given inventory
    """
    package_choices = None
    if os.path.exists(inventory_path):
        from ansible.inventory.manager import InventoryManager
        from ansible.parsing.dataloader import DataLoader
        ansible_loader = DataLoader()
        ansible_inventory = InventoryManager(loader=ansible_loader,
                                             sources=inventory_path)
        package_choices = list(ansible_inventory.hosts.keys())
        package_choices.extend(ansible_inventory.groups.keys())
        package_choices.extend(['all'])
    return package_choices


def obal_argument_parser(playbooks, package_choices):
    """
    Construct an argument parser with the given actions and package choices.
    """
    parser = argparse.ArgumentParser()

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-v", "--verbose",
                               action="count",
                               dest="verbose",
                               help="verbose output")

    advanced = parent_parser.add_argument_group('advanced arguments')
    advanced.add_argument('-e', '--extra-vars',
                          dest="extra_vars",
                          action="append",
                          default=[],
                          help="""set additional variables as key=value or
                          YAML/JSON, if filename prepend with @""")
    advanced.add_argument("--step",
                          action="store_true",
                          dest="step",
                          default=False,
                          help="interactive: confirm each task before running")
    advanced.add_argument('-t', '--tags',
                          dest='tags',
                          default=[],
                          action='append',
                          help="""only run plays and tasks tagged with these
                          values""")
    advanced.add_argument('--skip-tags',
                          dest='skip_tags',
                          default=[],
                          action='append',
                          help="""only run plays and tasks whose tags do not
                          match these values""")

    subparsers = parser.add_subparsers(dest='action',
                                       help="""which action to execute""")
    # Setting `required` outside of #add_subparser() is needed because
    # python2's #add_subparser() won't accept `required` as a field (even
    # though it's in the docs).
    subparsers.required = True

    for playbook in playbooks:
        subparser = subparsers.add_parser(playbook.name, parents=[parent_parser])
        subparser.set_defaults(playbook=playbook)

        if playbook.takes_package_parameter:
            subparser.add_argument('package',
                                   metavar='package',
                                   choices=package_choices,
                                   nargs='+',
                                   help="the package to build")

    if argcomplete:
        argcomplete.autocomplete(parser)

    return parser


def generate_ansible_args(inventory_path, args):
    """
    Generate the arguments to run ansible based on the parsed command line arguments
    """
    ansible_args = [args.playbook.path, '--inventory', inventory_path]
    if hasattr(args, 'package'):
        limit = ':'.join(args.package)
        ansible_args.extend(['--limit', limit])
    if args.verbose:
        ansible_args.append("-%s" % str("v" * args.verbose))
    for extra_var in args.extra_vars:
        ansible_args.extend(["-e", extra_var])
    if args.tags:
        ansible_args.append("--tags")
        ansible_args.append(",".join(args.tags))
    if args.skip_tags:
        ansible_args.append("--skip-tags")
        ansible_args.append(",".join(args.skip_tags))
    if args.step:
        ansible_args.append("--step")
    return ansible_args


def main(cliargs=None):  # pylint: disable=R0914
    """
    Main command
    """
    cfg_path = get_ansible_config_path()

    if os.path.exists(cfg_path):
        os.environ["ANSIBLE_CONFIG"] = cfg_path

    # this needs to be global, as otherwise PlaybookCLI fails
    # to set the verbosity correctly
    from ansible.utils.display import Display
    global display  # pylint: disable=C0103,W0603
    display = Display()

    inventory_path = os.path.join(os.getcwd(), 'package_manifest.yaml')

    package_choices = find_packages(inventory_path)
    playbooks = find_playbooks(get_playbooks_path())

    parser = obal_argument_parser(playbooks, package_choices)

    args = parser.parse_args(cliargs)

    if args.playbook.takes_package_parameter and not os.path.exists(inventory_path):
        print("Could not find your package_manifest.yaml")
        exit(1)

    from ansible.cli.playbook import PlaybookCLI

    ansible_args = generate_ansible_args(inventory_path, args)
    ansible_playbook = (["ansible-playbook"] + ansible_args)

    if args.verbose:
        print(ansible_playbook)

    cli = PlaybookCLI(ansible_playbook)
    cli.parse()
    exit_code = cli.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
