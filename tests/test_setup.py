"""Verify setup preserves legacy dependencies during the rhpkg opt-in rollout."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


@pytest.mark.parametrize('variables', [
    None,
    {'build_package_build_system': 'copr'},
    {'build_package_build_system': 'koji', 'build_package_use_koji_build': True},
    {'build_package_build_system': 'koji', 'build_package_releaser': 'koji'},
    {'build_package_build_system': 'koji', 'build_package_koji_command': 'brew'},
    {'build_package_build_system': 'koji', 'build_package_releaser': 'rhpkg'},
])
def test_setup_preserves_legacy_dependencies_without_installing_rhpkg(tmp_path, variables):
    root = Path(__file__).resolve().parent.parent
    if variables is not None:
        manifest = {'packages': {'vars': variables, 'hosts': {'package': {}}}}
        (tmp_path / 'package_manifest.yaml').write_text(yaml.safe_dump(manifest))
    log = tmp_path / 'packages.jsonl'
    env = dict(os.environ, PYTHONPATH=str(root), OBAL_SETUP_LOG=str(log),
               ANSIBLE_ACTION_PLUGINS=str(root / 'tests/fixtures/setup_actions'))
    result = subprocess.run([sys.executable, '-c', 'import obal; obal.main()', 'setup'],
                            cwd=tmp_path, env=env, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    assert result.returncode == 0, result.stdout
    packages = {name for line in log.read_text().splitlines() for name in json.loads(line)}
    assert 'git' in packages
    assert packages & {'git-annex', 'git-annex-standalone'}
    assert 'tito' in packages
    assert 'rhpkg' not in packages
