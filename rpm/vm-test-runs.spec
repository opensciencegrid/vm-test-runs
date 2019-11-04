Summary: OSG VMU test scripts
Name: vm-test-runs
Version: 0.1
Release: 1%{?dist}
Source0: %{name}-%{version}.tar.gz
License: Apache 2.0
BuildArch: noarch
Url: https://github.com/opensciencegrid/vm-test-runs/

Requires: libguestfs-tools
Requires: git

%description
Tools for running OSG VMU tests in the CHTC

%prep
%setup -q

%install
mkdir -p %{buildroot}/osgtest/runs

install -D rpm/osg-nightly-tests.service %{buildroot}/%{_unitdir}/osg-nightly-tests.service
install -D rpm/osg-nightly-tests.timer %{buildroot}/%{_unitdir}/osg-nightly-tests.timer
install -D rpm/vm-test-cleanup.service %{buildroot}/%{_unitdir}/vm-test-cleanup.service
install -D rpm/vm-test-cleanup.timer %{buildroot}/%{_unitdir}/vm-test-cleanup.timer

install -D -m 0755 bin/compare-rpm-versions %{buildroot}/%{_bindir}/compare-rpm-versions
install -D -m 0755 bin/list-rpm-versions %{buildroot}/%{_bindir}/list-rpm-versions
install -D -m 0755 bin/osg-run-tests %{buildroot}/%{_bindir}/osg-run-tests
install -D -m 0755 bin/vm-test-cleanup %{buildroot}/%{_bindir}/vm-test-cleanup

%files
%attr(1777,root,root) %dir /osgtest/runs

%{_bindir}/compare-rpm-versions
%{_bindir}/list-rpm-versions
%{_bindir}/osg-run-tests
%{_bindir}/vm-test-cleanup

%{_unitdir}/osg-nightly-tests.service
%{_unitdir}/osg-nightly-tests.timer
%{_unitdir}/vm-test-cleanup.service
%{_unitdir}/vm-test-cleanup.timer

%changelog
* Tue Oct 15 2019 Brian Lin <blin@ucsd.edu> 1.0.0-1
- Initial packaging
