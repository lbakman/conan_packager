from conans import tools
from conans.client import conan_api
from conans.errors import ConanException
from conans.model.ref import ConanFileReference
import os


class ConanPackager:
    _remote = "<repo>"
    _remote_user = "<username>"
    _remote_password = "<password>"
    _name = None
    _version = None
    _description = None
    _target_name = None
    _user = "user"
    _channel = "channel"
    _package = None
    _profile = None
    _conan = None
    _dependencies = None
    _working_path = os.getcwd()
    _deploy_path = os.path.join(os.getcwd(), "deploy")
    _empty_deploy_file = "nothing_to_deploy.txt"

    def __init__(self, user=None, channel=None, profile=None):
        # Create an instance of conan api
        (self._conan, _, _) = conan_api.Conan.factory()
        _, conanfile = self._conan.info("./conanfile.py", profile_name=profile)
        self._name = getattr(conanfile, "name", None)
        self._version = getattr(conanfile, "version", None)
        self._description = getattr(conanfile, "description", None)
        self._user = user if user else self._user
        self._channel = channel if channel else self._channel
        self._package = "%s/%s@%s/%s" % (self._name, self._version, self._user, self._channel)
        self._profile = profile if profile else None
        # Determine what we need to upload after the build
        (self._dependencies, _) = self._conan.info_nodes_to_build(".", profile_name=self._profile, build_modes=["missing"])

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    @property
    def package(self):
        return self._package

    @property
    def metadata(self):
        return {
            'name': self._name,
            'version': self._version,
            'package': self._package
        }

    def __str__(self):
        return "%s (%s)" % (self._package, self._description)

    # Determine which packages needs to be built and returns the list of packages.
    def determine_packages_to_upload(self):
        to_upload = []
        # Want to remove build requirements from this list
        for dependency in self._dependencies:
            to_upload.append(str(dependency))
        to_upload.append(str(self._package))
        return to_upload

    def install(self):
        self._conan.install(profile_name=self._profile, update=True, build=["missing"])

    def create(self, snapshot=False):
        # Export and create the package
        with tools.chdir(self._working_path):
            # Build and install dependencies.
            self._conan.install(profile_name=self._profile, update=True, no_imports=True, build=["missing"])

        with tools.chdir(self._working_path):
            conan_env = ["CONAN_SNAPSHOT=true"] if snapshot else None
            # Create the package.
            self._conan.create(".", user=self._user, channel=self._channel, profile_name=self._profile, env=conan_env)

    def deploy(self):
        # Remove old deploy directory
        tools.rmdir(self._deploy_path)
        tools.mkdir(self._deploy_path)
        # Install the package in the deploy folder
        with tools.chdir(self._deploy_path):
            self._conan.install_reference(reference=ConanFileReference.loads(self.package), profile_name=self._profile)
            # Check if anything was deployed
            if not os.listdir(self._deploy_path):
                # Nothing was deployed - create a txt file to ensure that something is there for the build server.
                open(self._empty_deploy_file, 'w').close()

    # Upload the specified packages.
    def upload_packages(self, packages=None, simulate=False):
        if packages:
            # Make sure we have an upload user token
            self._conan.authenticate(name=self._remote_user, password=self._remote_password, remote_name=self._remote)
            # Upload dependencies that we built
            for pkg in packages:
                print("Uploading package: %s" % pkg)
                try:
                    self._conan.upload(pkg, remote_name=self._remote, all_packages=True, force=True, skip_upload=simulate)
                except ConanException as e:
                    print("Unable to upload %s, continuing: %s" % (pkg, e))

    def upload_all(self, simulate=False):
        # Make sure we have an upload user token
        self._conan.authenticate(name=self._remote_user, password=self._remote_password, remote_name=self._remote)
        # Upload dependencies that we built
        for dependency in self._dependencies:
            self._conan.upload(dependency, remote_name=self._remote, all_packages=True,  skip_upload=simulate)
        # Upload this package
        self._conan.upload(self._package, remote_name=self._remote, all_packages=True, skip_upload=simulate)

    def remove(self):
        # Remove all versions of this package on the local machine. We do this to clean up old build on the build agent.
        pattern = "%s/*@%s/%s" % (self._name, self._user, self._channel)
        self._conan.remove(pattern, force=True)
