# Copyright (c) 2008-2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

from datetime import datetime
import glob
import json
import os
import os.path
import re
import shutil
import subprocess
from zipfile import ZipFile

from tito.builder.fetch import SourceStrategy
from tito.common import error_out, debug, run_command

class GitSourceStrategy(SourceStrategy):
    """
    Designed to be used for nightly or pull request builds only.
    It first copies source files from git, then copies the source file(s)
    over the top, so they're merged (patches etc can then be stored
    in git).
    """
    def fetch(self):
        if "source_dir" not in self.builder.args:
            raise Exception("Specify '--arg source_dir=...'")

        # Copy the live spec from our starting location. Unlike most builders,
        # we are not using a copy from a past git commit.
        self.spec_file = os.path.join(self.builder.rpmbuild_sourcedir,
                    '%s.spec' % self.builder.project_name)
        shutil.copyfile(
            os.path.join(self.builder.start_dir, '%s.spec' %
                self.builder.project_name),
            self.spec_file)

        gitrev = self._fetch_local()

        for s in os.listdir(self.builder.start_dir):
            if os.path.exists(os.path.join(self.builder.start_dir, s)):
                shutil.copyfile(
                    os.path.join(self.builder.start_dir, s),
                    os.path.join(self.builder.rpmbuild_sourcedir, os.path.basename(s)))
        print("  %s.spec" % self.builder.project_name)

        replacements = []
        src_files = run_command("find %s -type f" %
              os.path.join(self.builder.rpmbuild_sourcedir, 'archive')).split("\n")

        def filter_archives(path):
            base_name = os.path.basename(path)
            return ".tar" in base_name

        for i, s in enumerate(filter(filter_archives, src_files)):
            base_name = os.path.basename(s)
            debug("Downloaded file %s" % base_name)

            dest_filepath = os.path.join(self.builder.rpmbuild_sourcedir,
                    base_name)
            shutil.move(s, dest_filepath)
            self.sources.append(dest_filepath)

            # Add a line to replace in the spec for each source:
            source_regex = re.compile("^(source%s:\s*)(.+)$" % i, re.IGNORECASE)
            new_line = "Source%s: %s\n" % (i, base_name)
            replacements.append((source_regex, new_line))

        # Replace version in spec:
        version_regex = re.compile("^(version:\s*)(.+)$", re.IGNORECASE)
        self.version = self._get_version()
        print("Building version: %s" % self.version)
        replacements.append((version_regex, "Version: %s\n" % self.version))
        self.replace_in_spec(replacements)

        rel_date = datetime.utcnow().strftime("%Y%m%d%H%M")
        self.release = rel_date + gitrev
        print("Building release: %s" % self.release)
        run_command("sed -i '/^Release:/ s/%%/.%s%%/' %s" % (self.release, self.spec_file))


    """
    Generates the source file from a local repo, useful for generating
    packages of custom branches.
    It first copies source files from git, then copies the source file
    over the top, so they're merged (patches etc can then be stored
    in git).
    Takes the following arguments:
      source_dir: path to repo ("~/foreman")
    """
    def _fetch_local(self):

        source_dir = os.path.expanduser(self.builder.args['source_dir'][0])

        version_regex = re.compile("^(version:\s*)(.+)$", re.IGNORECASE)

        with open(self.spec_file, 'r') as spec:
            for line in spec.readlines():
                match = version_regex.match(line)
                if match:
                    version = match.group(2)

        if not version:
            error_out("Version not found in spec")

        old_dir = os.getcwd()
        os.chdir(source_dir)

        fetchdir = os.path.join(self.builder.rpmbuild_sourcedir, 'archive')
        if not os.path.exists(fetchdir):
          os.mkdir(fetchdir)

        arch_prefix = "-".join([self.builder.project_name, version])

        # git archive --format=tar.gz --prefix=pulp-2.15.0/ master > pulp-2.15.0.tar.gz

        with open("./%s.tar.gz" % arch_prefix, "w+") as archive:
            subprocess.call(["git", "archive", "--format=tar.gz", ("--prefix=%s/" % arch_prefix), "HEAD"], stdout=archive)

        sources = glob.glob("./*.tar.gz")
        print(sources)

        for srcfile in sources:
          debug("Copying %s from local source dir" % srcfile)
          shutil.move(srcfile, os.path.join(fetchdir, os.path.basename(srcfile)))

        gitrev = "local"
        gitsha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode('utf-8')
        if gitsha:
          gitrev = "git%s" % gitsha[0:7]

        os.chdir(old_dir)

        return gitrev

    def _get_version(self):
        """
        Get the version from the builder.
        Sources are configured at this point.
        """
        # Assuming source0 is a tar.gz we can extract a version from:
        base_name = os.path.basename(self.sources[0])
        debug("Extracting version from: %s" % base_name)

        # Example filename: tito-0.4.18.tar.gz:
        simple_version_re = re.compile(".*-(.*).(tar.gz|tgz|zip|tar.bz2|gem)")
        match = re.search(simple_version_re, base_name)
        if match:
            version = match.group(1)
        else:
            error_out("Unable to determine version from file: %s" % base_name)

        return version

    def replace_in_spec(self, replacements):
        """
        Replace lines in the spec file using the given replacements.
        Replacements are a tuple of a regex to look for, and a new line to
        substitute in when the regex matches.
        Replaces all lines with one pass through the file.
        """
        in_f = open(self.spec_file, 'r')
        out_f = open(self.spec_file + ".new", 'w')
        for line in in_f.readlines():
            for line_regex, new_line in replacements:
                match = re.match(line_regex, line)
                if match:
                    line = new_line
            out_f.write(line)

        in_f.close()
        out_f.close()
        shutil.move(self.spec_file + ".new", self.spec_file)
        shutil.copy(self.spec_file, "/tmp/spec.file")
