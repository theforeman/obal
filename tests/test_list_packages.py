import os

import pytest
import yaml

import obal


def write_inventory(tmp_path, inventory):
    inventory_path = tmp_path / 'package_manifest.yaml'
    inventory_path.write_text(yaml.safe_dump(inventory), encoding='utf-8')
    return inventory_path


def test_load_package_names_from_packages_and_child_groups(tmp_path):
    inventory_path = write_inventory(tmp_path, {
        'packages': {
            'hosts': {'direct-package': {}},
            'children': {'server': {}, 'client': {}},
        },
        'server': {'hosts': {'server-package': {}}},
        'client': {
            'hosts': {'client-package': {}},
            'children': {'shared': {}},
        },
        'shared': {'hosts': {'shared-package': {}}},
        'repoclosures': {'hosts': {'core-repoclosure': {}}},
        'copr_projects': {'hosts': {'foreman-copr': {}}},
    })

    assert obal.load_package_names(inventory_path) == [
        'client-package',
        'direct-package',
        'server-package',
        'shared-package',
    ]


def test_load_package_names_handles_cyclic_child_groups(tmp_path):
    inventory_path = write_inventory(tmp_path, {
        'packages': {'children': {'server': {}}},
        'server': {
            'hosts': {'server-package': {}},
            'children': {'packages': {}},
        },
    })

    assert obal.load_package_names(inventory_path) == ['server-package']


def test_list_packages_prints_sorted_packages(tmp_path, monkeypatch, capsys):
    inventory_path = write_inventory(tmp_path, {
        'packages': {'hosts': {'zlib': {}, 'ansible-core': {}}},
    })
    monkeypatch.setenv('OBAL_INVENTORY', os.fspath(inventory_path))

    obal.main(['list-packages'])

    assert capsys.readouterr().out == 'ansible-core\nzlib\n'


def test_list_packages_prints_nothing_for_empty_group(tmp_path, monkeypatch, capsys):
    inventory_path = write_inventory(tmp_path, {'packages': {'hosts': {}}})
    monkeypatch.setenv('OBAL_INVENTORY', os.fspath(inventory_path))

    obal.main(['list-packages'])

    assert capsys.readouterr().out == ''


def test_list_packages_reports_missing_inventory(tmp_path, monkeypatch, capsys):
    inventory_path = tmp_path / 'missing.yaml'
    monkeypatch.setenv('OBAL_INVENTORY', os.fspath(inventory_path))

    with pytest.raises(SystemExit) as error:
        obal.main(['list-packages'])

    assert error.value.code == 1
    assert "Could not read package inventory '{}'".format(inventory_path) in capsys.readouterr().err
