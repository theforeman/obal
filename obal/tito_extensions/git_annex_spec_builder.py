import os
import shutil
from distutils.version import LooseVersion as loose_version
from pkg_resources import require

from tito.compat import getstatusoutput
from tito.config_object import ConfigObject
from tito.builder import GitAnnexBuilder
from tito.builder.main import BuilderBase
from tito.common import error_out, debug, run_command, get_spec_version_and_release, \
    find_spec_like_file, get_relative_project_dir_cwd, warn_out, get_build_commit


class GitAnnexSpecBuilder(GitAnnexBuilder):

    def __init__(self, name=None, tag=None, build_dir=None,
                 config=None, user_config=None,
                 args=None, **kwargs):

        """
        name - Package name that is being built.

        version - Version and release being built.

        tag - The git tag being built.

        build_dir - Temporary build directory where we can safely work.

        config - Merged configuration. (global plus package specific)

        user_config - User configuration from ~/.titorc.

        args - Optional arguments specific to each builder. Can be passed
        in explicitly by user on the CLI, or via a release target config
        entry. Only for things which vary on invocations of the builder,
        avoid using these if possible.  *Given in the format of a dictionary
        of lists.*
        """
        ConfigObject.__init__(self, config=config)
        BuilderBase.__init__(self, name=name, build_dir=build_dir, config=config,
                             user_config=user_config, args=args, **kwargs)
        self.build_tag = tag

        self.build_version = self._get_build_version()
        self.git_commit_id = get_build_commit(tag=self.build_tag, test=True)

        if kwargs and 'options' in kwargs:
            warn_out("'options' no longer a supported builder constructor argument.")

        if self.config.has_option("requirements", "tito"):
            if loose_version(self.config.get("requirements", "tito")) > \
                    loose_version(require('tito')[0].version):
                error_out([
                    "tito version %s or later is needed to build this project." %
                    self.config.get("requirements", "tito"),
                    "Your version: %s" % require('tito')[0].version
                ])

        self.display_version = self._get_display_version()

        self.relative_project_dir = get_relative_project_dir_cwd(self.git_root)

        tgz_base = self._get_tgz_name_and_ver()
        self.tgz_filename = tgz_base + ".tar.gz"
        self.tgz_dir = tgz_base
        self.artifacts = []

        self.rpmbuild_gitcopy = os.path.join(self.rpmbuild_sourcedir,
                                             self.tgz_dir)

        # Used to make sure we only modify the spec file for a test build
        # once. The srpm method may be called multiple times during koji
        # releases to create the proper disttags, but we only want to modify
        # the spec file once.
        self.ran_setup_test_specfile = False

        # NOTE: These are defined later when/if we actually dump a copy of the
        # project source at the tag we're building. Only then can we search for
        # a spec file.
        self.spec_file_name = None
        self.spec_file = None

        # Set to path to srpm once we build one.
        self.srpm_location = None

    def _get_build_version(self):
        """
        Figure out the git tag and version-release we're building.
        """
        # Determine which package version we should build:
        build_version = None
        if self.build_tag:
            build_version = self.build_tag[len(self.project_name + "-"):]
        else:
            build_version = get_spec_version_and_release(self.start_dir,
                                                         find_spec_like_file(self.start_dir))
            self.build_tag = self._get_tag_for_version(build_version)

        self.spec_version = build_version.split('-')[0]
        self.spec_release = build_version.split('-')[-1]
        return build_version

    def _setup_sources(self):
        """
        Create a copy of the git source for the project at the point in time
        our build tag was created.

        Created in the temporary rpmbuild SOURCES directory.
        """
        self._create_build_dirs()
        working_path = os.path.join(os.getcwd(), self.relative_project_dir)

        debug('SETUP SOURCES')
        if self.relative_project_dir in os.path.join(os.getcwd(), ''):
            working_path = os.getcwd()
        debug("working_path: %s" % working_path)

        for directory, unused, filenames in os.walk(working_path):
            debug('WALK')
            dir_artifacts_with_path = [os.path.join(directory, f) for f in filenames]

            debug(dir_artifacts_with_path)
            for artifact in dir_artifacts_with_path:
                debug("  Copying source file %s" % artifact)
                if os.path.isfile(artifact):
                    shutil.copy(artifact, self.rpmbuild_gitcopy)
                    shutil.copy(artifact, self.rpmbuild_sourcedir)

        # NOTE: The spec file we actually use is the one exported by git
        # archive into the temp build directory. This is done so we can
        # modify the version/release on the fly when building test rpms
        # that use a git SHA1 for their version.
        self.spec_file_name = os.path.basename(find_spec_like_file(self.rpmbuild_sourcedir))
        self.spec_file = os.path.join(
            self.rpmbuild_sourcedir, self.spec_file_name)

        self.old_cwd = os.getcwd()
        if self.relative_project_dir not in os.path.join(os.getcwd(), ''):
            os.chdir(os.path.join(self.old_cwd, self.relative_project_dir))

        # NOTE: 'which' may not be installed... (docker containers)
        (status, output) = getstatusoutput("which git-annex")
        if status != 0:
            msg = "Please run '%s' as root." % self.package_manager.install(["git-annex"])
            error_out('%s' % msg)

        run_command("git-annex lock")
        annexed_files = run_command("git-annex find --include='*'").splitlines()
        run_command("git-annex get")
        run_command("git-annex unlock")
        debug("  Annex files: %s" % annexed_files)

        for annex in annexed_files:
            debug("Copying unlocked file %s" % annex)
            if os.path.isfile(os.path.join(self.rpmbuild_gitcopy, annex)):
                os.remove(os.path.join(self.rpmbuild_gitcopy, annex))
            shutil.copy(annex, self.rpmbuild_gitcopy)

        self._lock()
        os.chdir(self.old_cwd)
