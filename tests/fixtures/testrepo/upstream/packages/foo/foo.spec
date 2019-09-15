Name:           foo
Version:        1.0
Release:        1%{?dist}
Summary:        I love bars

License:        GPLv3+
Source0:        foo-source

Requires:       wget

%description
A fake RPM for foos and bars.

%prep
%autosetup

%build

%install
cp . %{buildroot}/

%files foo
foo-source

%changelog
* Tue Dec 11 2018 Foo Bar Man <foo@bar.foo> 1.0-1
- Initial version of the package
