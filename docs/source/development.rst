Developing Obal
===============

Obal is written with support for Python 2.7 and Python 3.5 or higher. To provide the command line we rely on the Python built in `argparse`_ and `Ansible`_. For testing we use `Pytest`_ but this is wrapped up with `Tox`_ to test multiple environments.

.. _argparse: https://docs.python.org/3/library/argparse.html
.. _Ansible: https://www.ansible.com/
.. _Pytest: https://pytest.org/
.. _Tox: https://tox.readthedocs.org/

Writing actions
---------------

All Ansible is contained in `obal/data`. There we have `playbooks`, `roles` and `modules`.

A `playbook` with `metadata` is considered an action and exposed to the user as such.

Writing playbooks
~~~~~~~~~~~~~~~~~

We have a slightly non-standard playbooks layout. Every playbook is contained in its own directory and named after the directory, like `release/release.yaml` for the `release` action. It can also contain a `metadata.obal.yaml`. While playbooks are pure Ansible, the metadata is the data Obal needs to extract to build a CLI.

Obal uses the inventory to operate on. The inventory is typically composed of packages, but there are some special hosts:

* localhost
* packages

As with regular Ansible, `localhost` is used to operate on the local machine. This is typically used to setup or work on environments.

Packages is the entire set of all packages. These are exposed on the command line to users so they can operate on a limited set of packages.

Within Ansible playbooks you can choose on which inventory items to operate through `hosts`. We set the additional limitation that hosts must always be a list. Our setup playbook is an example of a local connection:

.. literalinclude:: ../../obal/data/playbooks/setup/setup.yaml
  :language: yaml
  :caption: setup.yaml
  :emphasize-lines: 2,3

When dealing with packages we typically include the `package_variables` role to set various variables:

.. literalinclude:: ../../obal/data/playbooks/changelog/changelog.yaml
  :language: yaml
  :caption: changelog.yaml
  :emphasize-lines: 6,7

Exposing playbooks using metadata
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default Obal exposes a playbook based on its name. It can also automatically detect whether it accepts a packages parameter. To provide a better experience we introduce metadata via `metadata.obal.yaml` in the same directory.

An example:

.. literalinclude:: ../../tests/fixtures/playbooks/dummy/metadata.obal.yaml
  :language: yaml
  :caption: playbooks/dummy/metadata.obal.yaml

The help text is a top level key. The first line is used in ``obal --help``:

.. code-block:: none

   usage: obal [-h] action ...

   positional arguments:
     action          which action to execute
       dummy         Short description

   optional arguments:
     -h, --help      show this help message and exit


When we execute ``obal dummy --help`` we see more show up:

.. code-block:: none

    usage: obal dummy [-h] [-v] [-e EXTRA_VARS] [--step] [-t TAGS]
                  [--skip-tags SKIP_TAGS] [--automatic AUTOMATIC]
                  [--explicit MAPPED]
                  package [package ...]

   Short description

   Full text on multiple lines
   with an explicit newline

   positional arguments:
     package               the package to build

   optional arguments:
     -h, --help            show this help message and exit
     -v, --verbose         verbose output
     --automatic AUTOMATIC
                           Automatically determined parameter
     --explicit MAPPED     Explicitly specified parameter

   advanced arguments:
     -e EXTRA_VARS, --extra-vars EXTRA_VARS
                           set additional variables as key=value or YAML/JSON, if
                           filename prepend with @
     --step                interactive: confirm each task before running
     -t TAGS, --tags TAGS  only run plays and tasks tagged with these values
     --skip-tags SKIP_TAGS
                           only run plays and tasks whose tags do not match these
                           values


Help
^^^^

Help is a string at the top level in the metadata with some additional newline handling.

Multiple lines are joined but a single empty line indicates a newline. A double empty line indicates a new paragraph.

The first line is taken as a short description while the full text is included in the commands ``--help`` as can be seen above.

Variables
^^^^^^^^^

Variables is a mapping at the top level in the metadata.

For every variable the key is the variable in Ansible. It also needs a ``help``. The most minimal variant for a ``changelog`` playbook:

.. code-block:: yaml

    variables:
      changelog:
        help: The changelog message

This results into the following ``obal changelog --help`` output:

.. code-block:: none
  :emphasize-lines: 13,14

   usage: obal changelog [-h] [-v] [-e EXTRA_VARS] [--step] [-t TAGS]
                         [--skip-tags SKIP_TAGS] [--changelog CHANGELOG]
                         package [package ...]

   The changelog command writes a RPM changelog entry for the current version and release.

   positional arguments:
     package               the package to build

   optional arguments:
     -h, --help            show this help message and exit
     -v, --verbose         verbose output
     --changelog CHANGELOG
                           The text for the changelog entry

Now you might notice that this results in a ``obal changelog --changelog "my message"`` which feels a bit redundant. That's why there's mapping built in.


.. code-block:: yaml
  :emphasize-lines: 4

    variables:
      changelog:
        help: The changelog message
        parameter: --message

This results into the following help:

.. code-block:: none
  :emphasize-lines: 13

    usage: obal changelog [-h] [-v] [-e EXTRA_VARS] [--step] [-t TAGS]
                          [--skip-tags SKIP_TAGS] [--message CHANGELOG]
                          package [package ...]

    The changelog command writes a RPM changelog entry for the current version and release.

    positional arguments:
      package               the package to build

    optional arguments:
      -h, --help            show this help message and exit
      -v, --verbose         verbose output
      --message CHANGELOG   The text for the changelog entry

There is also support for automatic removal of namespaces.

.. code-block:: yaml
  :emphasize-lines: 2

    variables:
      changelog_author:
        help: The author of the changelog entry

When we run this within the changelog playbook, this is translated into:

.. code-block:: none

  --author CHANGELOG_AUTHOR
                        The author of the changelog entry

Fixing the tests
^^^^^^^^^^^^^^^^

First of all, the tests for various playbooks are stored in ``tests/test_playbooks.py``.

* ``test_takes_package_argument`` verifies whether there's an action parameter. Most playbooks do, but if yours doesn't then it must be added.
* ``test_is_documented`` verifies you're written a help text for your playbook.
* ``test_help`` captures the help texts in ``tests/fixtures/help`` to ensure there are no unintended changes. Rendered output is easier to review. Because manually copying output is stupid, we automatically store the output if the file is missing. To update the content, remove it and run the tests (``pytest tests/test_playbooks.py::test_help -v``). Note it marks that test as skipped. Running it again should mark it as passed.
