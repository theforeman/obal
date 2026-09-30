"""Verify setup follows package inventory rather than localhost defaults."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


@pytest.mark.parametrize('variables,rhpkg_required', [
    (None, False),
    ({'build_package_build_system': 'copr'}, False),
    ({'build_package_build_system': 'koji', 'build_package_use_koji_build': True}, False),
    ({'build_package_build_system': 'koji', 'build_package_releaser': 'koji'}, False),
    ({'build_package_build_system': 'koji', 'build_package_koji_command': 'brew'}, True),
])
def test_setup_installs_only_the_required_releaser(tmp_path, variables, rhpkg_required):
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
    assert 'tito' not in packages
    assert ('rhpkg' in packages) == rhpkg_required
