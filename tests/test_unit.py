from obal.data.module_utils.obal import get_specfile_sources, get_changelog_evr


def test_get_specfile_sources():
    sources = get_specfile_sources('tests/fixtures/testrepo/upstream/packages/hello/hello.spec')
    assert sources == ['http://ftp.gnu.org/gnu/hello/hello-2.10.tar.gz']

def test_get_changelog_evr():
    evr = get_changelog_evr('tests/fixtures/testrepo/upstream/packages/hello/hello.spec')
    assert evr == '2.10-2'
