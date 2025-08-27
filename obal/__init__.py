#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

"""
Obal is a wrapper around Ansible playbooks. They are exposed as a command line application.
"""

from __future__ import print_function

import os
from importlib import resources

import obsah


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


def main(cliargs=None, application_config=ApplicationConfig):  # pylint: disable=R0914
    """
    Main command
    """
    obsah.main(cliargs=cliargs, application_config=application_config)


if __name__ == '__main__':
    main()
