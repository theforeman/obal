#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

"""
Obal is a wrapper around Ansible playbooks. They are exposed as a command line application.
"""

from __future__ import print_function

import os
import sys
from importlib import resources

import obsah


INVENTORY_LIST_ACTIONS = ('list-groups', 'list-packages')


class ApplicationConfig(obsah.ApplicationConfig):
    """
    A class describing the where to find various files
    """

    @staticmethod
    def name():
        """
        Return the name as shown to the user in the ArgumentParser
        """
        return 'obal'

    @staticmethod
    def target_names():
        """
        Return the name of the target in the playbook if the playbook takes a parameter.
        """
        return ['packages', 'copr_projects']

    @staticmethod
    def metadata_name():
        """
        Return the name of the metadata file.
        """
        return 'metadata.obal.yaml'

    @staticmethod
    def data_path():
        """
        Return the data path. Houses playbooks and configs.
        """
        path = os.environ.get('OBAL_DATA')
        if path is None:
            path = str(resources.files(__name__) / 'data')

        return path

    @staticmethod
    def inventory_path():
        """
        Return the inventory path
        """
        return os.environ.get('OBAL_INVENTORY', os.path.join(os.getcwd(), 'package_manifest.yaml'))


def inventory_items(inventory_path, action):
    """
    Return user-defined package or group names from an Ansible inventory
    """
    from ansible.inventory.manager import InventoryManager  # pylint: disable=all
    from ansible.parsing.dataloader import DataLoader  # pylint: disable=all

    ansible_inventory = InventoryManager(
        loader=DataLoader(),
        sources=inventory_path,
    )

    if action == 'list-packages':
        packages = ansible_inventory.groups.get('packages')
        return sorted(host.name for host in packages.get_hosts()) if packages else []

    implicit_groups = {'all', 'ungrouped'}
    return sorted(set(ansible_inventory.groups) - implicit_groups)


def main(cliargs=None, application_config=ApplicationConfig):  # pylint: disable=R0914
    """
    Main command
    """
    arguments = cliargs if cliargs is not None else sys.argv[1:]

    if arguments and arguments[0] in INVENTORY_LIST_ACTIONS:
        inventory_path = application_config.inventory_path()
        targets = obsah.find_targets(inventory_path)
        parser = obsah.obsah_argument_parser(application_config, targets=targets)
        args = parser.parse_args(arguments)

        if not os.path.exists(inventory_path):
            parser.exit(1, "Could not find your inventory at {}".format(inventory_path))

        for item in inventory_items(inventory_path, args.action):
            print(item)
        return

    obsah.main(cliargs=arguments, application_config=application_config)


if __name__ == '__main__':
    main()
