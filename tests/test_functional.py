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
MOCK_SOURCES_DIR = os.path.join(FIXTURE_DIR, 'mock_sources')

DEFAULT_ARGS = []
if os.environ.get('TRAVIS', None):
    DEFAULT_ARGS.extend(['-e', 'ansible_remote_tmp=/tmp/ansible-remote'])


def git_init(path):
    subprocess.check_call(['git', 'init'], cwd=path)
    subprocess.check_call(['git', 'annex', 'init'], cwd=path)
    subprocess.check_call(['git', 'add', '.'], cwd=path)
    subprocess.check_call(['git', 'commit', '-a', '-m', 'init'], cwd=path)


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
        newcwd = os.path.join(repodir, repotype)
        os.chdir(newcwd)
        os.environ['PATH'] = "{}:{}".format(MOCKBIN_DIR, oldpath)
        os.environ['MOCKBIN_LOG'] = os.path.join(tempdir, 'mockbin.log')

        git_init(newcwd)

        func(*args, **kwargs)

        os.chdir(oldcwd)
        os.environ['PATH'] = oldpath
        os.environ.pop('MOCKBIN_LOG')

        shutil.rmtree(tempdir, ignore_errors=True)

    return func_wrapper


def run_obal(args, exitcode):
    with pytest.raises(SystemExit) as excinfo:
        obal.main(args + DEFAULT_ARGS)
    assert excinfo.value.code == exitcode


def assert_obal_success(args):
    run_obal(args, 0)


def assert_obal_failure(args):
    run_obal(args, 2)


def assert_mockbin_log(content):
    expected_log = "\n".join(content)
    expected_log = expected_log.replace('{pwd}', os.getcwd())
    with open(os.environ['MOCKBIN_LOG']) as mockbinlog:
        log = mockbinlog.read().strip()
        assert log == expected_log


def setup_upstream(upstream_path):
    # create a cloneable upstream repo, what we ship in fixtures is not
    git_init(upstream_path)
    subprocess.check_call(['git', 'annex', 'addurl', '--file',
                           'packages/hello/hello-2.10.tar.gz',
                           'http://ftp.gnu.org/gnu/hello/hello-2.10.tar.gz'],
                          cwd=upstream_path)
    subprocess.check_call(['git', 'commit', '-a', '-m', 'add hello'],
                          cwd=upstream_path)


@obal_cli_test(repotype='upstream')
def test_obal_noargs():
    assert_obal_failure([])


@obal_cli_test(repotype='upstream')
def test_obal_check_upstream_hello():
    assert_obal_success(['check', 'hello'])

    expected_log = [
        "koji list-tagged --quiet --latest obaltest-nightly-rhel7 hello",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_scratch_upstream_hello():
    assert_obal_success(['scratch', 'hello'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "koji list-pkgs --tag obaltest-nightly-rhel7 --package hello --quiet",
        "tito release --scratch dist-git -y",
        "koji watch-task 1234",
        "koji taskinfo -v 1234",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_scratch_upstream_hello_nowait():
    assert_obal_success(['scratch', 'hello', '-e', 'build_package_wait=False'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "koji list-pkgs --tag obaltest-nightly-rhel7 --package hello --quiet",
        "tito release --scratch dist-git -y"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_release_upstream_hello():
    assert_obal_success(['release', 'hello'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "koji list-tagged --quiet --latest obaltest-nightly-rhel7 hello",
        "koji list-pkgs --tag obaltest-nightly-rhel7 --package hello --quiet",
        "tito release dist-git -y",
        "koji watch-task 1234",
        "koji taskinfo -v 1234",
        "koji wait-repo --build=hello-2.10-1.el7 --target obaltest-nightly-rhel7"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_release_upstream_hello_nowait():
    assert_obal_success(['release', 'hello', '-e', 'build_package_wait=False'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "koji list-tagged --quiet --latest obaltest-nightly-rhel7 hello",
        "koji list-pkgs --tag obaltest-nightly-rhel7 --package hello --quiet",
        "tito release dist-git -y",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_release_upstream_hello_nowaitrepo():
    assert_obal_success(['release', 'hello', '-e', 'build_package_waitrepo=False'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "koji list-tagged --quiet --latest obaltest-nightly-rhel7 hello",
        "koji list-pkgs --tag obaltest-nightly-rhel7 --package hello --quiet",
        "tito release dist-git -y",
        "koji watch-task 1234",
        "koji taskinfo -v 1234",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_nightly_upstream_hello():
    assert_obal_success(['nightly', 'hello', '--source', os.path.join(MOCK_SOURCES_DIR, 'hello-2.10.tar.gz'), '--githash', '0123456789abcdef'])

    expected_log = [
        "koji list-pkgs --tag obaltest-nightly-rhel7 --package hello --quiet",
        "tito release dist-git -y --arg jenkins_job=hello-master-release",
        "koji watch-task 1234",
        "koji taskinfo -v 1234",
        "koji wait-repo --build=hello-2.10-1.el7 --target obaltest-nightly-rhel7"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_scratch_downstream_hello_nowait():
    assert_obal_success(['scratch', 'hello', '-e', 'build_package_wait=False'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "brew list-pkgs --tag obaltest-dist-git-rhel-7 --package hello --quiet",
        "tito release obaltest-scratch-rhel-7 -y"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_release_downstream_hello_nowait():
    assert_obal_success(['release', 'hello', '-e', 'build_package_wait=False'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "brew list-tagged --quiet --latest obaltest-6.3.0-rhel-7-candidate hello",  # noqa: E501
        "brew list-pkgs --tag obaltest-dist-git-rhel-7 --package hello --quiet",
        "tito release obaltest-dist-git-rhel-7 -y",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_scratch_downstream_hello():
    assert_obal_success(['scratch', 'hello'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "brew list-pkgs --tag obaltest-dist-git-rhel-7 --package hello --quiet",
        "tito release obaltest-scratch-rhel-7 -y",
        "brew watch-task 1234",
        "brew taskinfo -v 1234",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_scratch_downstream_hello_wait_download_logs():
    assert_obal_success(['scratch', 'hello', '-e', 'build_package_download_logs=True'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "brew list-pkgs --tag obaltest-dist-git-rhel-7 --package hello --quiet",
        "tito release obaltest-scratch-rhel-7 -y",
        "brew watch-task 1234",
        "brew download-logs -r 1234",
        "brew taskinfo -v 1234",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_scratch_downstream_hello_wait_download_rpms():
    assert_obal_success(['scratch', 'hello', '-e', 'build_package_download_rpms=True'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "brew list-pkgs --tag obaltest-dist-git-rhel-7 --package hello --quiet",
        "tito release obaltest-scratch-rhel-7 -y",
        "brew watch-task 1234",
        "brew taskinfo -v 1234",
        "brew download-task 1234",
        "createrepo {pwd}/downloaded_rpms/rhel7"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_release_downstream_hello():
    assert_obal_success(['release', 'hello'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "brew list-tagged --quiet --latest obaltest-6.3.0-rhel-7-candidate hello",  # noqa: E501
        "brew list-pkgs --tag obaltest-dist-git-rhel-7 --package hello --quiet",
        "tito release obaltest-dist-git-rhel-7 -y",
        "brew watch-task 1234",
        "brew taskinfo -v 1234",
        # the build and target in the next command are "wrong" because the
        # output from our mocked brew is not dynamic
        "brew wait-repo --build=hello-2.10-1.el7 --target obaltest-nightly-rhel7"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_release_downstream_hello_wait_download_logs():
    assert_obal_success(['release', 'hello', '-e', 'build_package_download_logs=True'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "brew list-tagged --quiet --latest obaltest-6.3.0-rhel-7-candidate hello",  # noqa: E501
        "brew list-pkgs --tag obaltest-dist-git-rhel-7 --package hello --quiet",
        "tito release obaltest-dist-git-rhel-7 -y",
        "brew watch-task 1234",
        "brew download-logs -r 1234",
        "brew taskinfo -v 1234",
        # the build and target in the next command are "wrong" because the
        # output from our mocked brew is not dynamic
        "brew wait-repo --build=hello-2.10-1.el7 --target obaltest-nightly-rhel7"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_release_downstream_hello_wait_download_rpms():
    assert_obal_success(['release', 'hello', '-e', 'build_package_download_rpms=True'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "brew list-tagged --quiet --latest obaltest-6.3.0-rhel-7-candidate hello",  # noqa: E501
        "brew list-pkgs --tag obaltest-dist-git-rhel-7 --package hello --quiet",
        "tito release obaltest-dist-git-rhel-7 -y",
        "brew watch-task 1234",
        "brew taskinfo -v 1234",
        # the build and target in the next command are "wrong" because the
        # output from our mocked brew is not dynamic
        "brew wait-repo --build=hello-2.10-1.el7 --target obaltest-nightly-rhel7",
        "brew download-task 1234",
        "createrepo {pwd}/downloaded_rpms/rhel7",
    ]
    assert_mockbin_log(expected_log)

@obal_cli_test(repotype='downstream')
def test_obal_release_downstream_hello_nowaitrepo():
    assert_obal_success(['release', 'hello', '-e', 'build_package_waitrepo=False'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "brew list-tagged --quiet --latest obaltest-6.3.0-rhel-7-candidate hello",
        "brew list-pkgs --tag obaltest-dist-git-rhel-7 --package hello --quiet",
        "tito release obaltest-dist-git-rhel-7 -y",
        "brew watch-task 1234",
        "brew taskinfo -v 1234",
    ]
    assert_mockbin_log(expected_log)

@obal_cli_test(repotype='upstream')
def test_obal_update_upstream_hello():
    assert_obal_success(['update', 'hello', '-e', 'version=2.8'])

    assert not os.path.exists('packages/hello/hello-2.10.tar.gz')
    assert not os.path.islink('packages/hello/hello-2.10.tar.gz')
    assert os.path.islink('packages/hello/hello-2.8.tar.gz')

    with open('packages/hello/hello.spec') as specfile:
        specfilecontent = specfile.read()

    assert 'Version:        2.8' in specfilecontent
    assert '- Release hello 2.8' in specfilecontent


@obal_cli_test(repotype='downstream')
def test_obal_update_downstream_hello():
    setup_upstream('../upstream/')

    assert_obal_success(['update', 'hello'])

    assert not os.path.exists('packages/hello/hello-2.9.tar.gz')
    assert not os.path.islink('packages/hello/hello-2.9.tar.gz')
    assert os.path.islink('packages/hello/hello-2.10.tar.gz')

    with open('packages/hello/hello.spec') as specfile:
        specfilecontent = specfile.read()

    # a downstream update overwrites all the data with whatever is in upstream
    # thus we expect to see no mention of 2.9 in the specfile anymore
    # we also don't expect a changelog entry added
    assert 'Version:        2.10' in specfilecontent
    assert 'Source0:        http://ftp.gnu.org/gnu' in specfilecontent
    assert '2.9' not in specfilecontent
    assert '- Release hello' not in specfilecontent


@obal_cli_test(repotype='downstream')
def test_obal_update_downstream_with_version_hello():
    setup_upstream('../upstream/')

    assert_obal_success(['update', 'hello1', '-e', 'version=2.10'])

    assert not os.path.exists('packages/hello1/hello-2.9.tar.gz')
    assert not os.path.islink('packages/hello1/hello-2.9.tar.gz')
    assert os.path.islink('packages/hello1/hello-2.10.tar.gz')

    with open('packages/hello1/hello.spec') as specfile:
        specfilecontent = specfile.read()

    # a downstream update overwrites all the data with whatever is in upstream
    # thus we expect to see no mention of 2.9 in the specfile anymore
    # we also don't expect a changelog entry added
    assert 'Version:        2.10' in specfilecontent
    assert 'Source0:        http://ftp.gnu.org/gnu' in specfilecontent
    assert 'Version:        2.9' not in specfilecontent
    assert '- Release hello' in specfilecontent


@obal_cli_test(repotype='empty')
def test_obal_add_downstream_hello():
    setup_upstream('../upstream/')

    assert_obal_success(['add', 'hello'])

    assert os.path.islink('packages/hello/hello-2.10.tar.gz')


@obal_cli_test(repotype='upstream')
def test_obal_repoclosure():
    assert_obal_success(['repoclosure', 'core-repoclosure'])

    expected_log = [
        "repoclosure --config {pwd}/repoclosure/el7.conf --tempcache --newest --repoid downloaded_rpms --lookaside el7-base"  # noqa: E501
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_repoclosure_with_downloaded_rpms():
    # create a folder under downloaded_rpms to pretend we have a repo there
    os.makedirs('downloaded_rpms/rhel7')

    assert_obal_success(['repoclosure', 'dist-repoclosure'])

    expected_log = [
        "repoclosure --config {pwd}/repoclosure/el7.conf --tempcache --newest --repoid downloaded_rpms --repofrompath=downloaded_rpms,./downloaded_rpms/rhel7 --lookaside el7-base"  # noqa: E501
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_repoclosure_katello_with_downloaded_rpms():
    # create a folder under downloaded_rpms to pretend we have a repo there
    os.makedirs('downloaded_rpms/rhel7')

    assert_obal_success(['repoclosure', 'katello-repoclosure'])

    expected_log = [
        "repoclosure --config {pwd}/repoclosure/el7.conf --tempcache --newest --repoid el7-katello --repoid downloaded_rpms --repofrompath=downloaded_rpms,./downloaded_rpms/rhel7 --lookaside el7-base"  # noqa: E501
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='copr')
def test_obal_scratch_copr_hello_nowait():
    assert_obal_success(['scratch', 'hello', '-e', 'build_package_wait=False'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "copr-cli create copr-repo-scratch --chroot epel-7-x86_64 --description 'Scratch Builds' --unlisted-on-hp on --repo http://mirror.centos.org/centos/7/sclo/x86_64/rh/",  # noqa: E501
        "copr-cli edit-chroot copr-repo-scratch/epel-7-x86_64 --packages 'scl-utils-build rh-ruby24-build'",  # noqa: E501
        "tito build --srpm --scl=copr-scl",
        "copr-cli build --nowait copr-repo-scratch hello-2.10-1.src.rpm"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='copr')
def test_obal_scratch_copr_hello():
    assert_obal_success(['scratch', 'hello'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "copr-cli create copr-repo-scratch --chroot epel-7-x86_64 --description 'Scratch Builds' --unlisted-on-hp on --repo http://mirror.centos.org/centos/7/sclo/x86_64/rh/",  # noqa: E501
        "copr-cli edit-chroot copr-repo-scratch/epel-7-x86_64 --packages 'scl-utils-build rh-ruby24-build'",  # noqa: E501
        "tito build --srpm --scl=copr-scl",
        "copr-cli build copr-repo-scratch hello-2.10-1.src.rpm",
        # copr-cli build waits by default, so there is no "watch-build" step here
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='copr')
def test_obal_release_copr_hello_nowait():
    assert_obal_success(['release', 'hello', '-e', 'build_package_wait=False'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "tito release copr -y",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='copr')
def test_obal_release_copr_hello():
    assert_obal_success(['release', 'hello'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "tito release copr -y",
        "copr-cli watch-build"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_bump_release_hello():
    assert_obal_success(['bump-release', 'hello'])

    assert '2' == subprocess.check_output(['rpmspec', '-q', '--queryformat=%{release}', '--srpm', '--undefine=dist', 'packages/hello/hello.spec'], universal_newlines=True)  # noqa: E501


@obal_cli_test(repotype='upstream')
def test_obal_bump_release_hello_with_changelog():
    assert_obal_success(['bump-release', 'hello', '-e', "changelog='New-package-release'"])
    output = subprocess.check_output(['rpmspec', '-q', '--queryformat=%{changelogtext}', '--srpm', '--undefine=dist', 'packages/hello/hello.spec'], universal_newlines=True)  # noqa: E501

    assert 'New-package-release' in output


@obal_cli_test(repotype='upstream')
def test_obal_lint_hello():
    assert_obal_success(['lint', 'hello'])

    assert_mockbin_log(["rpmlint --file {pwd}/packages/hello/.rpmlintrc {pwd}/packages/hello"])


@obal_cli_test(repotype='upstream_with_epoch')
def test_obal_lint_hello_with_epoch():
    assert_obal_success(['lint', 'hello'])

    assert_mockbin_log(["rpmlint --file {pwd}/packages/hello/.rpmlintrc {pwd}/packages/hello"])


@obal_cli_test(repotype='upstream_bad_changelog')
def test_obal_lint_bad_changelog():
    assert_obal_failure(['lint', 'hello'])

    assert_mockbin_log(["rpmlint --file {pwd}/packages/hello/.rpmlintrc {pwd}/packages/hello"])


@obal_cli_test(repotype='upstream')
def test_obal_changelog():
    assert_obal_success(['changelog', 'hello'])
    output = subprocess.check_output(['rpmspec', '-q', '--queryformat=%{changelogtext}', '--srpm', '--undefine=dist', 'packages/hello/hello.spec'], universal_newlines=True)  # noqa: E501

    assert 'rebuilt' in output


@obal_cli_test(repotype='upstream')
def test_obal_changelog_custom():
    assert_obal_success(['changelog', 'hello', '-e', "changelog='New-package-release'"])
    output = subprocess.check_output(['rpmspec', '-q', '--queryformat=%{changelogtext}', '--srpm', '--undefine=dist', 'packages/hello/hello.spec'], universal_newlines=True)  # noqa: E501

    assert 'New-package-release' in output


@obal_cli_test(repotype='upstream')
def test_obal_srpm():
    assert_obal_success(['srpm', 'hello'])
    assert_mockbin_log(['tito build --srpm --offline --output {pwd}/SRPMs'])
