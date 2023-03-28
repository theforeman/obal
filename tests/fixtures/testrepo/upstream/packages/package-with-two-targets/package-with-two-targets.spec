Name:           package-with-two-targets
Version:        1.0
Release:        1%{?dist}
Summary:        I love bars

License:        GPLv3+
Source0:        package-with-two-targets-source

Requires:       wget

%description
A fake RPM for package-with-two-targetss and bars.

%prep
%autosetup

%build

%install
cp . %{buildroot}/

%files
package-with-two-targets-source

%changelog
* Tue Dec 11 2018 Foo Bar Man <package-with-two-targets@bar.package-with-two-targets> 1.0-1
- Initial version of the package
