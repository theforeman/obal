Name:           package-with-existing-build
Version:        1.0
Release:        1%{?dist}
Summary:        I love bars

License:        GPLv3+
Source0:        package-with-existing-build-source

Requires:       wget

%description
A fake RPM for package-with-existing-builds and bars.

%prep
%autosetup

%build

%install
cp . %{buildroot}/

%files
package-with-existing-build-source

%changelog
* Tue Dec 11 2018 Foo Bar Man <package-with-existing-build@bar.package-with-existing-build> 1.0-1
- Initial version of the package
