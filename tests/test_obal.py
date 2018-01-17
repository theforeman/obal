import os
import obal


FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
)


def test_find_no_packages():
    packages = obal.find_packages(os.path.join(FIXTURE_DIR, 'nope.yaml'))
    assert packages is None


def test_find_packages():
    packages = obal.find_packages(os.path.join(FIXTURE_DIR, 'inventory.yaml'))
    assert packages
    assert 'testpackage' in packages
