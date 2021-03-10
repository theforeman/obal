from obal.data.module_utils.obal import get_specfile_sources


def test_get_specfile_sources():
    sources = get_specfile_sources('tests/fixtures/testrepo/upstream/packages/hello/hello.spec')
    assert sources == ['http://ftp.gnu.org/gnu/hello/hello-2.10.tar.gz']
