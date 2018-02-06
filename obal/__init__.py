#!/usr/bin/env python2
# PYTHON_ARGCOMPLETE_OK

from __future__ import print_function

import argparse
import os
import sys

from pkg_resources import resource_filename

try:
    import argcomplete
except ImportError:
    argcomplete = None

_PLAYBOOKS = {
    'add': 'add_package.yml',
    'check': 'check_package.yml',
    'release': 'release_package.yml',
    'scratch': 'scratch_build.yml',
    'update': 'update_package.yml'
}


def find_packages(inventory_path):
    package_choices = None
    if os.path.exists(inventory_path):
        from ansible.inventory.manager import InventoryManager
        from ansible.parsing.dataloader import DataLoader
        ansible_loader = DataLoader()
        ansible_inventory = InventoryManager(loader=ansible_loader,
                                             sources=inventory_path)
        package_choices = ansible_inventory.hosts.keys()
        package_choices.extend(ansible_inventory.groups.keys())
    return package_choices


def obal_argument_parser(package_choices):
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--extra-vars',
                        dest="extra_vars",
                        action="append",
                        default=[],
                        help="""set additional variables as key=value or
                        YAML/JSON, if filename prepend with @""")
    parser.add_argument("-v", "--verbose",
                        action="count",
                        dest="verbose",
                        help="verbose output")
    parser.add_argument("--step",
                        action="store_true",
                        dest="step",
                        default=False,
                        help="interactive: confirm each task before running")
    parser.add_argument('-t', '--tags',
                        dest='tags',
                        default=[],
                        action='append',
                        help="""only run plays and tasks tagged with these
                        values""")
    parser.add_argument('--skip-tags',
                        dest='skip_tags',
                        default=[],
                        action='append',
                        help="""only run plays and tasks whose tags do not
                        match these values""")

    parser.add_argument("action",
                        choices=_PLAYBOOKS.keys(),
                        help="""which action to execute""")
    parser.add_argument('package',
                        metavar='package',
                        choices=package_choices,
                        nargs='+',
                        help="the package to build")

    if argcomplete:
        argcomplete.autocomplete(parser)

    return parser


def generate_ansible_args(inventory_path, playbook_path, args):
    limit = ':'.join(args.package)
    ansible_args = [playbook_path, '--inventory', inventory_path, '--limit',
                    limit]
    for extra_var in args.extra_vars:
        ansible_args.extend(["-e", extra_var])
    if args.verbose:
        ansible_args.append("-%s" % str("v" * args.verbose))
    if args.tags:
        ansible_args.append("--tags")
        ansible_args.append(",".join(args.tags))
    if args.skip_tags:
        ansible_args.append("--skip-tags")
        ansible_args.append(",".join(args.skip_tags))
    if args.step:
        ansible_args.append("--step")
    return ansible_args


def main():
    packaging_playbooks_path = resource_filename(__name__, 'data')
    cfg_path = os.path.join(packaging_playbooks_path, 'ansible.cfg')

    if os.path.exists(cfg_path):
        os.environ["ANSIBLE_CONFIG"] = cfg_path

    # this needs to be global, as otherwise PlaybookCLI fails
    # to set the verbosity correctly
    from ansible.utils.display import Display
    global display
    display = Display()

    inventory_path = os.path.join(os.getcwd(), 'package_manifest.yaml')

    package_choices = find_packages(inventory_path)

    parser = obal_argument_parser(package_choices)

    args = parser.parse_args()

    playbook = _PLAYBOOKS[args.action]
    playbook_path = os.path.join(packaging_playbooks_path, playbook)

    if not os.path.exists(inventory_path):
        print("Could not find your package_manifest.yaml")
        exit(1)
    if not os.path.exists(playbook_path):
        print("Could not find the packaging playbooks")
        exit(1)

    from ansible.cli.playbook import PlaybookCLI

    ansible_args = generate_ansible_args(inventory_path, playbook_path, args)
    ansible_playbook = (["ansible-playbook"] + ansible_args)

    if args.verbose:
        print(ansible_playbook)

    cli = PlaybookCLI(ansible_playbook)
    cli.parse()
    exit_code = cli.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
