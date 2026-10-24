Obal actions
============

.. argparse::
   :ref: obal.obal_argument_parser
   :prog: obal

available options
-----------------

Options can be either set on the command line via `-e key=val` or in the `package_manifest` file (preferred).

* `build_package_build_system`: which build system should be used, default: `koji`, supported: `koji`, `copr`
* `build_package_releaser`: for the `koji` build system, choose `tito` (default), `koji` (direct SRPM submission), or `rhpkg` (explicit dist-git opt-in). `build_package_use_koji_build: true` selects `koji` when no releaser is set.
* `build_package_koji_command`: the Koji client executable, default: `brew` for the `rhpkg` releaser and `koji` otherwise. Explicit executable overrides are preserved.
* `build_package_rhpkg_command`: the rhpkg client executable, default: `rhpkg`.
* `rhpkg_targets`: explicit build contexts and destination tags for the `rhpkg` releaser; see below.
* `build_package_tito_args`: any args that should be passed to `tito`, default: `''`
* `build_package_scratch`: when building a package, should a scratch build be done, default: `false` (unless you run `obal scratch`, of course)
* `build_package_test`: when building a package with `tito`, should `--test` be passed to it, default: `false`
* `build_package_tito_releaser_args`: any args that should be passed to `tito release`, default: `[]`
* `build_package_wait`: wait for package to be built on the build system, default: `true`
* `build_package_download_logs`: download build logs from the build system after the build has finished, default: `false`
* `build_package_download_rpms`: download completed RPMs, default: `false`
* `build_package_waitrepo`: wait for release builds to appear in the target repository, default: `false`
* `build_package_koji_whitelist_check`: check package registration before release submission or tagging, default: `true` for rhpkg releases and `false` otherwise. Rhpkg scratch builds skip this check.
* `diff_package_type`: which build system to query for built packages, default: `koji`, supported: `koji`, `copr`
* `diff_package_koji_command`: the client used for package comparisons, default: `brew` for the `rhpkg` releaser and `koji` otherwise.
* `diff_package_skip`: should packages be built without checking the build system, default: `true`
* `scl`: which SCL, if any, belong the packages to, defaults to `False` (no SCL)

Opting in to rhpkg releases
--------------------------

Existing inventories continue to use Tito and ``rel-eng/releasers.conf``.
Defining ``rhpkg_targets`` alone does not change the releaser. To enable rhpkg,
set ``build_package_releaser: rhpkg`` explicitly in the package manifest.
COPR continues to use ``build_package_build_system: copr``.

Install and configure rhpkg separately using the repositories available in your
Brew environment, and authenticate the Brew client before releasing. ``obal
setup`` retains its existing Tito dependencies and does not try to install
rhpkg from Fedora, EPEL, or CentOS repositories. Git credentials must permit
dist-git cloning and pushing, and rhpkg credentials must permit lookaside uploads
and build submission.

For example::

    packages:
      vars:
        build_package_build_system: koji
        build_package_releaser: rhpkg
        rhpkg_targets:
          - name: rhel9
            distgit_branch: foreman-5.0-rhel-9
            build_target: foreman-5.0-rhel-9-candidate
            dist: .el9
            macros:
              foremandist: .fm5_0
            tags:
              - foreman-5.0-rhel-9-candidate
              - foreman-client-5.0-rhel-9-candidate
      hosts:
        nodejs-graphql: {}

Each target requires a unique path-safe ``name``, a ``distgit_branch``, a
``build_target``, a ``dist`` RPM macro value, and a nonempty list of destination
``tags``. ``distgit_package`` defaults to the inventory package name. Optional
``scl`` and ``macros`` provide the RPM context for querying the NVR and preparing
scratch SRPMs. This context must match the RPM macros configured for the build
target. Configure ``dist`` and ``scl`` in their own fields rather than in
``macros``.

Build targets select where to build; destination tags select where the result
must be available. Targets producing the same NVR must be combined into a
single target with multiple tags. Configure destinations in ``rhpkg_targets``;
if ``koji_tags`` is also set, its tag names and RPM contexts must agree.
Tito releaser configuration is not translated into rhpkg targets.

``obal release`` reuses an existing complete NVR and applies only missing tags.
For a missing NVR, it stages the spec sources and patches, uploads lookaside
sources, pushes dist-git, and submits the build through rhpkg. ``obal check`` and
``obal verify-koji-tag`` use the configured destination tags and default to Brew.
Package registration and query failures stop release submission or tagging.

``obal scratch`` prepares a local SRPM and submits it directly through the
configured Koji/Brew executable. It does not push dist-git or apply destination
tags. The rhpkg releaser uses sources declared by the spec and does not support
Tito test builders or ``setup_sources_git``. Those options remain available to
existing Tito inventories.

Asynchronous release and scratch actions save task receipts under
``.tmp/rhpkg`` in the inventory directory. Rerun the same action with waiting
enabled to finish it. Pending tasks are reused only when their NVR, target,
spec, and source bytes still match. Failed or cancelled scratch tasks permit a
new submission; task query failures preserve the receipt. After a successful
scratch action completes, a subsequent scratch action can submit a new build.
