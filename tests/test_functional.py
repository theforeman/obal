import functools
import os
import shutil
import subprocess
import tempfile
import pytest
import obal


FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
)

TESTREPO_DIR = os.path.join(FIXTURE_DIR, 'testrepo')
MOCKBIN_DIR = os.path.join(FIXTURE_DIR, 'mockbin')

DEFAULT_ARGS = []
if os.environ.get('TRAVIS', None):
    DEFAULT_ARGS.extend(['-e', 'ansible_remote_tmp=/tmp/ansible-remote'])


def obal_cli_test(func=None, repotype='upstream'):
    if func is None:
        return functools.partial(obal_cli_test, repotype=repotype)

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        tempdir = tempfile.mkdtemp()
        repodir = os.path.join(tempdir, 'repo')
        shutil.copytree(TESTREPO_DIR, repodir)

        oldcwd = os.getcwd()
        oldpath = os.environ['PATH']
        os.chdir(os.path.join(repodir, repotype))
        os.environ['PATH'] = "{}:{}".format(MOCKBIN_DIR, oldpath)
        os.environ['MOCKBIN_LOG'] = os.path.join(tempdir, 'mockbin.log')

        subprocess.check_call(['git', 'init'])

        func(*args, **kwargs)

        os.chdir(oldcwd)
        os.environ['PATH'] = oldpath
        os.environ.pop('MOCKBIN_LOG')

        shutil.rmtree(tempdir, ignore_errors=True)

    return func_wrapper


def run_obal(args, exitcode):
    with pytest.raises(SystemExit) as excinfo:
        obal.main(DEFAULT_ARGS + args)
    assert excinfo.value.code == exitcode


def assert_obal_success(args):
    run_obal(args, 0)


def assert_obal_failure(args):
    run_obal(args, 2)


def assert_mockbin_log(content):
    expected_log = "\n".join(content)
    expected_log = expected_log.replace('{bin}', MOCKBIN_DIR)
    with open(os.environ['MOCKBIN_LOG']) as mockbinlog:
        log = mockbinlog.read().strip()
        assert log == expected_log


def setup_upstream(upstream_path):
    # create a cloneable upstream repo, what we ship in fixtures is not
    subprocess.check_call(['git', 'init'], cwd=upstream_path)
    subprocess.check_call(['git', 'annex', 'init'], cwd=upstream_path)
    subprocess.check_call(['git', 'add', '.'], cwd=upstream_path)
    subprocess.check_call(['git', 'annex', 'addurl', '--file',
                           'packages/hello/hello-2.10.tar.gz',
                           'http://ftp.gnu.org/gnu/hello/hello-2.10.tar.gz'],
                          cwd=upstream_path)
    subprocess.check_call(['git', 'commit', '-a', '-m', 'init'],
                          cwd=upstream_path)


@obal_cli_test(repotype='upstream')
def test_obal_noargs():
    assert_obal_failure([])


@obal_cli_test(repotype='upstream')
def test_obal_scratch_upstream_hello():
    assert_obal_success(['scratch', 'hello'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "['{bin}/tito', 'release', '--scratch', 'dist-git', '-y']"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_release_upstream_hello():
    assert_obal_success(['release', 'hello'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "['{bin}/tito', 'release', 'dist-git', '-y']",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_scratch_downstream_hello():
    assert_obal_success(['scratch', 'hello'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "['{bin}/tito', 'release', 'obaltest-scratch-rhel-7', '-y']"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_release_downstream_hello():
    assert_obal_success(['release', 'hello'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "['{bin}/brew', 'list-tagged', '--quiet', 'satellite-6.3.0-rhel-7-candidate', 'hello']",  # noqa: E501
        "['{bin}/tito', 'release', 'obaltest-dist-git-rhel-7', '-y']",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_scratch_downstream_hello_wait():
    assert_obal_success(['scratch', 'hello', '--tags', 'wait,download'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "['{bin}/tito', 'release', 'obaltest-scratch-rhel-7', '-y']",
        "['{bin}/brew', 'watch-task']",
        "['{bin}/brew', 'download-logs', '-r']",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_release_downstream_hello_wait():
    assert_obal_success(['release', 'hello', '--tags', 'wait,download'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "['{bin}/brew', 'list-tagged', '--quiet', 'satellite-6.3.0-rhel-7-candidate', 'hello']",  # noqa: E501
        "['{bin}/tito', 'release', 'obaltest-dist-git-rhel-7', '-y']",
        "['{bin}/brew', 'watch-task']",
        "['{bin}/brew', 'download-logs', '-r']",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_update_downstream_hello():
    setup_upstream('../upstream/')

    assert_obal_success(['update', 'hello'])

    assert not os.path.exists('packages/hello/hello-2.9.tar.gz')
    assert not os.path.islink('packages/hello/hello-2.9.tar.gz')
    assert os.path.islink('packages/hello/hello-2.10.tar.gz')


@obal_cli_test(repotype='empty')
def test_obal_add_downstream_hello():
    setup_upstream('../upstream/')

    assert_obal_success(['add', 'hello'])

    assert os.path.islink('packages/hello/hello-2.10.tar.gz')
