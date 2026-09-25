Configuration paths
===================

Obal uses its bundled playbooks and Ansible configuration by default, and
looks for ``package_manifest.yaml`` in the current working directory. You can
override these paths with environment variables:

``OBAL_INVENTORY``
  The path to the package manifest. The default is
  ``$PWD/package_manifest.yaml``.

``OBAL_DATA``
  The directory containing Obal's data files. By default, Obal uses the
  ``data`` directory installed with the Python package. The default playbook
  directory and Ansible configuration are ``playbooks`` and ``ansible.cfg``
  below this directory.

``OBSAH_PLAYBOOKS``
  The playbook directory. This takes precedence over the ``playbooks``
  directory below ``OBAL_DATA``.

``OBSAH_ANSIBLE_CFG``
  The path to ``ansible.cfg``. This takes precedence over ``ansible.cfg``
  below ``OBAL_DATA``.

The playbook and Ansible configuration variables use the ``OBSAH`` prefix
because Obal inherits their handling from the Obsah command-line framework.

For example, to use a manifest and playbooks stored outside the current
working directory, run:

.. code-block:: console

   $ OBAL_INVENTORY=/path/to/package_manifest.yaml \
       OBSAH_PLAYBOOKS=/path/to/playbooks obal scratch package-name
