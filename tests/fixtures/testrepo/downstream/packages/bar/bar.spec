Name:           bar
Version:        1.0
Release:        1%{?dist}
Summary:        Fake bar package with a local (non-URL) source, mimicking nodejs bundle tarballs

License:        GPLv3+
Source0:        bar-old-source

%description
A fake RPM used to test cleanup of renamed local sources during obal update.

%prep
%autosetup

%build

%install
cp . %{buildroot}/

%files
bar-old-source

%changelog
* Tue Dec 11 2018 Foo Bar Man <foo@bar.foo> 1.0-1
- Initial version of the package
