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

DEFAULT_ARGS = ['-e', 'build_package_srpm_directory="/tmp/SRPMs"']


def git_init(path):
    subprocess.check_call(['git', 'init', '--initial-branch', 'develop'], cwd=path)
    subprocess.check_call(['git', 'config', 'user.email', 'test@example.test'])
    subprocess.check_call(['git', 'config', 'user.name', 'Test CI'])
    subprocess.check_call(['git', 'annex', 'init'], cwd=path)
    subprocess.check_call(['git', '-c', 'annex.largefiles=nothing', 'add', '.'], cwd=path)
    subprocess.check_call(['git', 'commit', '-a', '-m', 'init'], cwd=path)


def obal_cli_test(func=None, repotype='upstream'):
    if func is None:
        return functools.partial(obal_cli_test, repotype=repotype)

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        __tracebackhide__ = True
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


def assert_in_mockbin_log(content):
    __tracebackhide__ = True

    with open(os.environ['MOCKBIN_LOG']) as mockbinlog:
        log = mockbinlog.read().strip()

    if not isinstance(content, list):
        content = [content]

    for entry in content:
        expected_log_entry = entry.replace('{pwd}', os.getcwd())
        assert expected_log_entry in log


def assert_not_in_mockbin_log(content):
    __tracebackhide__ = True
    expected_log_entry = content.replace('{pwd}', os.getcwd())
    with open(os.environ['MOCKBIN_LOG']) as mockbinlog:
        log = mockbinlog.read().strip()
        assert expected_log_entry not in log


def assert_mockbin_log(content):
    __tracebackhide__ = True
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
        "koji buildinfo hello-2.10-2.el7",
        "koji latest-build --quiet obaltest-nightly-rhel7 hello",
        "koji buildinfo hello-2.10-2.el8",
        "koji latest-build --quiet obaltest-nightly-el8 hello"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_scratch_with_tito_upstream_hello():
    assert_obal_success(['scratch', 'hello'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "koji build obaltest-nightly-rhel7 /tmp/SRPMs/hello-2.10-2.src.rpm --scratch",
        "koji watch-task 1234",
        "koji build obaltest-nightly-el8 /tmp/SRPMs/hello-2.10-2.src.rpm --scratch",
        "koji watch-task 1234"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_scratch_with_tito_upstream_hello_nowait():
    assert_obal_success(['scratch', 'hello', '-e', 'build_package_wait=False'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "koji build obaltest-nightly-rhel7 /tmp/SRPMs/hello-2.10-2.src.rpm --scratch",
        "koji build obaltest-nightly-el8 /tmp/SRPMs/hello-2.10-2.src.rpm --scratch"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_scratch_with_koji_upstream_hello():
    assert_obal_success(['scratch', 'hello', '-e', 'build_package_use_koji_build=true'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "koji build obaltest-nightly-rhel7 /tmp/SRPMs/hello-2.10-2.src.rpm --scratch",
        "koji watch-task 1234",
        "koji build obaltest-nightly-el8 /tmp/SRPMs/hello-2.10-2.src.rpm --scratch",
        "koji watch-task 1234",
    ]
    assert_mockbin_log(expected_log)
    assert os.path.exists('/tmp/SRPMs/hello-2.10-2.src.rpm')


@obal_cli_test(repotype='upstream')
def test_obal_scratch_with_koji_upstream_hello_nowait():
    assert_obal_success(['scratch', 'hello', '-e', 'build_package_wait=False', '-e', 'build_package_use_koji_build=true'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "koji build obaltest-nightly-rhel7 /tmp/SRPMs/hello-2.10-2.src.rpm --scratch",
        "koji build obaltest-nightly-el8 /tmp/SRPMs/hello-2.10-2.src.rpm --scratch"
    ]
    assert_mockbin_log(expected_log)
    assert os.path.exists('/tmp/SRPMs/hello-2.10-2.src.rpm')


@obal_cli_test(repotype='upstream')
def test_obal_release_with_koji_upstream_hello():
    assert_obal_success(['release', 'hello', '-e', 'build_package_use_koji_build=true'])

    expected_log = [
        "koji buildinfo hello-2.10-2.el7",
        "koji latest-build --quiet obaltest-nightly-rhel7 hello",
        "koji latest-build --quiet obaltest-nightly-rhel7 hello",
        "koji build obaltest-nightly-rhel7 /tmp/SRPMs/hello-2.10-2.src.rpm",
        "koji watch-task 1234",
        "koji buildinfo hello-2.10-2.el8",
        "koji latest-build --quiet obaltest-nightly-el8 hello",
        "koji latest-build --quiet obaltest-nightly-el8 hello",
        "koji build obaltest-nightly-el8 /tmp/SRPMs/hello-2.10-2.src.rpm",
        "koji watch-task 1234",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_release_with_koji_upstream_existing_build():
    assert_obal_success(['release', 'package-with-existing-build', '-e', 'build_package_use_koji_build=true'])

    expected_log = [
        "koji buildinfo package-with-existing-build-1.0-1.el7",
        "koji latest-build --quiet obaltest-nightly-rhel7 package-with-existing-build",
        "koji tag-build obaltest-nightly-rhel7 package-with-existing-build-1.0-1.el7",
        "koji buildinfo package-with-existing-build-1.0-1.el8",
        "koji latest-build --quiet obaltest-nightly-el8 package-with-existing-build",
        "koji latest-build --quiet obaltest-nightly-el8 package-with-existing-build",
        "koji build obaltest-nightly-el8 /tmp/SRPMs/package-with-existing-build-1.0-1.src.rpm",
        "koji watch-task 1234",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_release_with_koji_upstream_two_target_tags():
    assert_obal_success(['release', 'package-with-two-targets', '-e', 'build_package_use_koji_build=true'])

    expected_log = [
        "koji buildinfo package-with-two-targets-1.0-1.el8",
        "koji latest-build --quiet obaltest-nightly-el8 package-with-two-targets",
        "koji latest-build --quiet obaltest-nightly-el8 package-with-two-targets",
        "koji build obaltest-nightly-el8 /tmp/SRPMs/package-with-two-targets-1.0-1.src.rpm",
        "koji watch-task 1234",
        "koji buildinfo package-with-two-targets-1.0-1.el8",
        "koji latest-build --quiet obalclient-nightly-el8 package-with-two-targets",
        "koji tag-build obalclient-nightly-el8 package-with-two-targets-1.0-1.el8"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_release_with_koji_upstream_whitelist_check():
    assert_obal_success(['release', 'package-with-existing-build', '-e', 'build_package_use_koji_build=true', '-e', 'build_package_koji_whitelist_check=true'])

    expected_log = [
        "koji buildinfo package-with-existing-build-1.0-1.el7",
        "koji latest-build --quiet obaltest-nightly-rhel7 package-with-existing-build",
        "koji tag-build obaltest-nightly-rhel7 package-with-existing-build-1.0-1.el7",
        "koji buildinfo package-with-existing-build-1.0-1.el8",
        "koji latest-build --quiet obaltest-nightly-el8 package-with-existing-build",
        "koji list-pkgs --tag obaltest-nightly-el8 --package package-with-existing-build --quiet",
        "koji latest-build --quiet obaltest-nightly-el8 package-with-existing-build",
        "koji build obaltest-nightly-el8 /tmp/SRPMs/package-with-existing-build-1.0-1.src.rpm",
        "koji watch-task 1234",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_release_upstream_hello():
    assert_obal_success(['release', 'hello'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "koji buildinfo hello-2.10-2.el7",
        "koji latest-build --quiet obaltest-nightly-rhel7 hello",
        "koji buildinfo hello-2.10-2.el8",
        "koji latest-build --quiet obaltest-nightly-el8 hello",
        "tito release --yes dist-git",
        "koji watch-task 1234",
        "koji taskinfo -v 1234",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_release_upstream_hello_whitelist_check():
    assert_obal_success(['release', 'hello', '-e', 'build_package_koji_whitelist_check=true'])

    expected_log_entry = "koji list-pkgs --tag obaltest-nightly-rhel7 --package hello --quiet"
    assert_in_mockbin_log(expected_log_entry)


@obal_cli_test(repotype='upstream')
def test_obal_release_upstream_hello_no_whitelist_check():
    assert_obal_success(['release', 'hello', '-e', 'build_package_koji_whitelist_check=false'])

    unexpected_log_entry = "koji list-pkgs --tag obaltest-nightly-rhel7 --package hello --quiet"
    assert_not_in_mockbin_log(unexpected_log_entry)


@obal_cli_test(repotype='upstream')
def test_obal_release_upstream_hello_nowait():
    assert_obal_success(['release', 'hello', '-e', 'build_package_wait=False'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "koji buildinfo hello-2.10-2.el7",
        "koji latest-build --quiet obaltest-nightly-rhel7 hello",
        "koji buildinfo hello-2.10-2.el8",
        "koji latest-build --quiet obaltest-nightly-el8 hello",
        "tito release --yes dist-git",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_release_upstream_hello_waitrepo():
    assert_obal_success(['release', 'hello', '-e', 'build_package_waitrepo=True'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "koji buildinfo hello-2.10-2.el7",
        "koji latest-build --quiet obaltest-nightly-rhel7 hello",
        "koji buildinfo hello-2.10-2.el8",
        "koji latest-build --quiet obaltest-nightly-el8 hello",
        "tito release --yes dist-git",
        "koji watch-task 1234",
        "koji taskinfo -v 1234",
        "koji wait-repo --build=hello-2.10-1.el7 --target obaltest-nightly-rhel7"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_nightly_upstream_hello():
    assert_obal_success(['nightly', 'hello', '--source', os.path.join(MOCK_SOURCES_DIR, 'hello-2.10.tar.gz'), '--githash', '0123456789abcdef'])

    expected_log = [
        "tito release --yes dist-git --arg jenkins_job=hello-master-release",
        "koji watch-task 1234",
        "koji taskinfo -v 1234",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_release_downstream_hello_whitelist_check():
    assert_obal_success(['release', 'hello', '-e', 'build_package_koji_whitelist_check=true'])

    expected_log_entry = "brew list-pkgs --tag obaltest-dist-git-rhel-7 --package hello --quiet"
    assert_in_mockbin_log(expected_log_entry)


@obal_cli_test(repotype='downstream')
def test_obal_release_downstream_hello_no_whitelist_check():
    assert_obal_success(['release', 'hello', '-e', 'build_package_koji_whitelist_check=false'])

    unexpected_log_entry = "brew list-pkgs --tag obaltest-dist-git-rhel-7 --package hello --quiet"
    assert_not_in_mockbin_log(unexpected_log_entry)


@obal_cli_test(repotype='downstream')
def test_obal_scratch_downstream_hello_nowait():
    assert_obal_success(['scratch', 'hello', '-e', 'build_package_wait=False'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "tito release --yes obaltest-scratch-rhel-7"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_release_downstream_hello_nowait():
    assert_obal_success(['release', 'hello', '-e', 'build_package_wait=False'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "brew list-tagged --quiet --latest obaltest-6.3.0-rhel-7-candidate tfm-hello",  # noqa: E501
        "tito release --yes obaltest-dist-git-rhel-7",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_scratch_downstream_hello():
    assert_obal_success(['scratch', 'hello'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "tito release --yes obaltest-scratch-rhel-7",
        "brew watch-task 1234",
        "brew taskinfo -v 1234",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_scratch_downstream_hello_wait_download_logs():
    assert_obal_success(['scratch', 'hello', '-e', 'build_package_download_logs=True'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "tito release --yes obaltest-scratch-rhel-7",
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
        "tito release --yes obaltest-scratch-rhel-7",
        "brew watch-task 1234",
        "brew taskinfo -v 1234",
        "brew download-task --arch=noarch --arch=x86_64 1234",
        "createrepo {pwd}/downloaded_rpms/rhel7"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_release_downstream_hello():
    assert_obal_success(['release', 'hello'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "brew list-tagged --quiet --latest obaltest-6.3.0-rhel-7-candidate tfm-hello",  # noqa: E501
        "tito release --yes obaltest-dist-git-rhel-7",
        "brew watch-task 1234",
        "brew taskinfo -v 1234",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_release_downstream_hello_wait_download_logs():
    assert_obal_success(['release', 'hello', '-e', 'build_package_download_logs=True'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "brew list-tagged --quiet --latest obaltest-6.3.0-rhel-7-candidate tfm-hello",  # noqa: E501
        "tito release --yes obaltest-dist-git-rhel-7",
        "brew watch-task 1234",
        "brew download-logs -r 1234",
        "brew taskinfo -v 1234",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='downstream')
def test_obal_release_downstream_hello_wait_download_rpms():
    assert_obal_success(['release', 'hello', '-e', 'build_package_download_rpms=True'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "brew list-tagged --quiet --latest obaltest-6.3.0-rhel-7-candidate tfm-hello",  # noqa: E501
        "tito release --yes obaltest-dist-git-rhel-7",
        "brew watch-task 1234",
        "brew taskinfo -v 1234",
        "brew download-task --arch=noarch --arch=x86_64 1234",
        "createrepo {pwd}/downloaded_rpms/rhel7",
    ]
    assert_mockbin_log(expected_log)

@obal_cli_test(repotype='downstream')
def test_obal_release_downstream_hello_waitrepo():
    assert_obal_success(['release', 'hello', '-e', 'build_package_waitrepo=True'])

    assert os.path.exists('packages/hello/hello-2.9.tar.gz')

    expected_log = [
        "brew list-tagged --quiet --latest obaltest-6.3.0-rhel-7-candidate tfm-hello",  # noqa: E501
        "tito release --yes obaltest-dist-git-rhel-7",
        "brew watch-task 1234",
        "brew taskinfo -v 1234",
        # the build and target in the next command are "wrong" because the
        # output from our mocked brew is not dynamic
        "brew wait-repo --build=hello-2.10-1.el7 --target obaltest-nightly-rhel7"
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
    assert 'Release:        1' in specfilecontent
    assert '- Release hello 2.8' in specfilecontent
    assert '%global prerelease' not in specfilecontent


@obal_cli_test(repotype='upstream')
def test_obal_update_upstream_hello_prerelease():
    assert_obal_success(['update', 'hello', '-e', 'version=2.8', '-e', 'prerelease=rc1'])

    assert not os.path.exists('packages/hello/hello-2.10.tar.gz')
    assert not os.path.islink('packages/hello/hello-2.10.tar.gz')
    assert os.path.islink('packages/hello/hello-2.8.tar.gz')

    with open('packages/hello/hello.spec') as specfile:
        specfilecontent = specfile.read()

    assert 'Version:        2.8' in specfilecontent
    assert 'Release:        1' in specfilecontent
    assert '- Release hello 2.8' in specfilecontent
    assert '%global prereleasesource rc1' in specfilecontent


@obal_cli_test(repotype='upstream')
def test_obal_update_upstream_hello_keeprelease():
    assert_obal_success(['update', 'hello', '-e', 'version=2.8', '-e', 'release=keep'])

    assert not os.path.exists('packages/hello/hello-2.10.tar.gz')
    assert not os.path.islink('packages/hello/hello-2.10.tar.gz')
    assert os.path.islink('packages/hello/hello-2.8.tar.gz')

    with open('packages/hello/hello.spec') as specfile:
        specfilecontent = specfile.read()

    assert 'Version:        2.8' in specfilecontent
    assert 'Release:        2' in specfilecontent
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
        "dnf repoclosure",
        "--refresh",
        "--newest",
        "--config",
        "repoclosure/yum.conf",
        "--check el7-katello",
        "--repo el7-katello",
        "--repo el7-base"
    ]
    assert_in_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_repoclosure_with_downloaded_rpms():
    # create a folder under downloaded_rpms to pretend we have a repo there
    os.makedirs('downloaded_rpms/rhel7')

    assert_obal_success(['repoclosure', 'dist-repoclosure'])

    expected_log = [
        "dnf repoclosure",
        "--newest",
        "--refresh",
        "--config",
        "repoclosure/yum.conf",
        "--repofrompath downloaded_rpms,{pwd}/downloaded_rpms/rhel7",
        "--check downloaded_rpms",
        "--repo el7-base"
    ]
    assert_in_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_repoclosure_katello_with_downloaded_rpms():
    # create a folder under downloaded_rpms to pretend we have a repo there
    os.makedirs('downloaded_rpms/rhel7')

    assert_obal_success(['repoclosure', 'katello-repoclosure'])

    expected_log = [
        "dnf repoclosure",
        "--newest",
        "--refresh",
        "--config",
        "repoclosure/yum.conf",
        "--repofrompath downloaded_rpms,{pwd}/downloaded_rpms/rhel7",
        "--check el7-katello",
        "--check downloaded_rpms",
        "--repo el7-base"
    ]
    assert_in_mockbin_log(expected_log)

@obal_cli_test(repotype='upstream')
def test_obal_repoclosure_with_check_repo():
    assert_obal_success(['repoclosure', 'hello', '--check', 'https://test.example.com/myrepo', '--dist', 'rhel7'])

    expected_log = [
        "dnf repoclosure",
        "--newest",
        "--refresh",
        "--config",
        "repoclosure/yum.conf",
        "--check repo0",
        "--repofrompath repo0,https://test.example.com/myrepo",
        "--repo el7-base"
    ]

    assert_in_mockbin_log(expected_log)

@obal_cli_test(repotype='copr')
def test_obal_scratch_copr_hello_nowait():
    assert_obal_success(['scratch', 'hello', '-e', 'build_package_wait=False'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "copr-cli list example",
        "copr-cli create example/foreman-1234 --description foreman-1234 --appstream off --chroot epel-7-x86_64 --unlisted-on-hp on --delete-after-days 4",  # noqa: E501
        "copr-cli edit-chroot example/foreman-1234/epel-7-x86_64 --repos http://mirror.centos.org/centos/7/sclo/x86_64/rh/ --packages 'rh-ruby24-build scl-utils-build' --upload-comps {pwd}/comps/comps-el8.xml",  # noqa: E501
        "copr-cli get-package example/foreman-1234 --name hello --with-all-builds",
        "copr-cli build example/foreman-1234 /tmp/SRPMs/hello-2.10-1.src.rpm --chroot epel-7-x86_64 --nowait"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='copr')
def test_obal_scratch_copr_hello():
    assert_obal_success(['scratch', 'hello'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "copr-cli list example",
        "copr-cli create example/foreman-1234 --description foreman-1234 --appstream off --chroot epel-7-x86_64 --unlisted-on-hp on --delete-after-days 4",  # noqa: E501
        "copr-cli edit-chroot example/foreman-1234/epel-7-x86_64 --repos http://mirror.centos.org/centos/7/sclo/x86_64/rh/ --packages 'rh-ruby24-build scl-utils-build' --upload-comps {pwd}/comps/comps-el8.xml",  # noqa: E501
        "copr-cli get-package example/foreman-1234 --name hello --with-all-builds",
        "copr-cli build example/foreman-1234 /tmp/SRPMs/hello-2.10-1.src.rpm --chroot epel-7-x86_64 --nowait",
        "copr-cli watch-build 5678"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='copr')
def test_obal_release_copr_hello_nowait():
    assert_obal_success(['release', 'hello', '-e', 'build_package_wait=False'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "copr-cli get-package example/foreman --name hello --with-all-builds",
        "copr-cli build example/foreman /tmp/SRPMs/hello-2.10-1.src.rpm --chroot epel-7-x86_64 --nowait"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='copr')
def test_obal_release_copr_hello():
    assert_obal_success(['release', 'hello'])

    assert os.path.exists('packages/hello/hello-2.10.tar.gz')

    expected_log = [
        "copr-cli get-package example/foreman --name hello --with-all-builds",
        "copr-cli build example/foreman /tmp/SRPMs/hello-2.10-1.src.rpm --chroot epel-7-x86_64 --nowait",
        "copr-cli watch-build 5678"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_bump_release_hello():
    assert_obal_success(['bump-release', 'hello'])

    assert '3' == subprocess.check_output(['rpmspec', '-q', '--queryformat=%{release}', '--srpm', '--undefine=dist', 'packages/hello/hello.spec'], universal_newlines=True)  # noqa: E501


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

    assert '- New-package-release' in output


@obal_cli_test(repotype='upstream')
def test_obal_srpm():
    assert_obal_success(['srpm', 'hello', 'foo'])

    assert os.path.exists('SRPMs/foo-1.0-1.src.rpm')
    assert os.path.exists('SRPMs/hello-2.10-2.src.rpm')


@obal_cli_test(repotype='upstream')
def test_obal_mock():
    assert_obal_success(['mock', 'hello', 'foo', '--config', 'mock/el7.cfg'])

    expected_log = [
        "mock --recurse --chain -r mock/el7.cfg --localrepo {pwd}/mock_builds SRPMs/foo-1.0-1.src.rpm SRPMs/hello-2.10-2.src.rpm"
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_verify_tag():
    assert_obal_success(['verify-koji-tag', 'obaltest-nightly-rhel7'])

    expected_log = ['koji list-pkgs --quiet --tag obaltest-nightly-rhel7']
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='upstream')
def test_obal_verify_tag_all():
    assert_obal_success(['verify-koji-tag', 'all'])

    expected_log = [
        'koji list-pkgs --quiet --tag obalclient-nightly-el8',
        'koji list-pkgs --quiet --tag obaltest-nightly-el8',
        'koji list-pkgs --quiet --tag obaltest-nightly-rhel7'
    ]
    assert_mockbin_log(expected_log)

@obal_cli_test(repotype='copr')
def test_copr_project_one_chroot():
    assert_obal_success(['copr-project', 'foreman'])

    expected_log = [
        "copr-cli list example",
        "copr-cli create example/foreman --description foreman --appstream off --chroot epel-7-x86_64",  # noqa: E501
        "copr-cli edit-chroot example/foreman/epel-7-x86_64 --repos http://mirror.centos.org/centos/7/sclo/x86_64/rh/ --packages 'rh-ruby24-build scl-utils-build' --upload-comps {pwd}/comps/comps-el8.xml",  # noqa: E501

    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='copr')
def test_copr_project_many_chroots():
    assert_obal_success(['copr-project', 'client'])

    expected_log = [
        "copr-cli list example",
        "copr-cli create example/foreman-client --description foreman-client --appstream off --chroot rhel-9-x86_64 --chroot rhel-8-x86_64 --chroot rhel-7-x86_64",  # noqa: E501
        "copr-cli edit-chroot example/foreman-client/rhel-9-x86_64",
        "copr-cli edit-chroot example/foreman-client/rhel-8-x86_64",
        "copr-cli edit-chroot example/foreman-client/rhel-7-x86_64"

    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='copr')
def test_copr_project_fork():
    assert_obal_success(['copr-project', 'client', '-e copr_project_fork_from=client-test'])

    expected_log = [
        "copr-cli list example",
        "copr-cli fork example/client-test example/foreman-client",
        "copr-cli edit-chroot example/foreman-client/rhel-9-x86_64",
        "copr-cli edit-chroot example/foreman-client/rhel-8-x86_64",
        "copr-cli edit-chroot example/foreman-client/rhel-7-x86_64",
    ]
    assert_mockbin_log(expected_log)


@obal_cli_test(repotype='copr')
def test_copr_project_fork_already_exists():
    assert_obal_success(['copr-project', 'client', '-e copr_project_fork_from=client-test', '-e copr_project_user=existing-fork'])

    expected_log = [
        "copr-cli list existing-fork",
        "copr-cli edit-chroot existing-fork/foreman-client/rhel-9-x86_64",
        "copr-cli edit-chroot existing-fork/foreman-client/rhel-8-x86_64",
        "copr-cli edit-chroot existing-fork/foreman-client/rhel-7-x86_64",
    ]
    assert_mockbin_log(expected_log)
