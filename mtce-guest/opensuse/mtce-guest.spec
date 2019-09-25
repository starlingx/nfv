Summary: Maintenance Guest Server/Agent Package
Name: mtce-guest
Version: 1.0.0
%define patchlevel %{tis_patch_ver}
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: System/Base
URL: https://opendev.org/starlingx/nfv

Source0: %{name}-%{version}.tar.gz

BuildRequires: openssl
BuildRequires: openssl-devel
BuildRequires: libjson-c3
BuildRequires: libjson-c-devel
BuildRequires: libevent
BuildRequires: libevent-devel
BuildRequires: libuuid1
BuildRequires: libuuid-devel
BuildRequires: fm-common
BuildRequires: fm-common-dev
BuildRequires: mtce-common-devel >= 1.0
BuildRequires: systemd
BuildRequires: systemd-sysvinit
BuildRequires: sysvinit-tools
BuildRequires: insserv-compat
BuildRequires: cppcheck
BuildRequires: gcc-c++

%description
Maintenance Guest Agent Service and Server assists in VM guest
heartbeat control and failure reporting at the controller level.

%package -n mtce-guestAgent
Summary: Maintenance Guest Agent Package
Group: System/Base
Requires: dpkg
Requires: time
Requires: libjson-c3
Requires: libstdc++6
Requires: glibc
Requires: fm-common >= 1.0
Requires: bash >= 4.4
Requires: libgcc_s1
Requires: libevent >= 2.0.21
Requires: libuuid1
Requires: systemd
Requires: systemd-sysvinit
Requires: sysvinit-tools
Requires: insserv-compat
Requires: logrotate
Requires: openssl


%description -n mtce-guestAgent
Maintenance Guest Agent Service assists in
VM guest heartbeat control and failure reporting at the controller
level.

%package -n mtce-guestServer
Summary: Maintenance Guest Server Package
Group: System/Base
Requires: util-linux
Requires: bash >= 4.4
Requires: systemd
Requires: dpkg
Requires: libjson-c3
Requires: libjson-c-devel
Requires: libstdc++6
Requires: glibc
Requires: fm-common >= 1.0
Requires: libgcc_s1
Requires: libevent >= 2.0.21
Requires: libuuid1
Requires: logrotate
Requires: openssl

%description -n mtce-guestServer
Maintenance Guest Server assists in VM guest
heartbeat control and failure reporting at the worker level.

%define local_bindir /usr/local/bin

%prep
%setup -n %{name}-%{version}/src

# build mtce-guestAgent and mtce-guestServer package
%build
VER=%{version}
MAJOR=$(echo $VER | awk -F . '{print $1}')
MINOR=$(echo $VER | awk -F . '{print $2}')
make MAJOR=$MAJOR MINOR=$MINOR %{?_smp_mflags} build

# install mtce-guestAgent and mtce-guestServer package
%install
make install \
     DESTDIR=%{buildroot} \
     PREFIX=%{buildroot}/usr/local \
     SYSCONFDIR=%{buildroot}%{_sysconfdir} \
     LOCALBINDIR=%{buildroot}%{local_bindir} \
     UNITDIR=%{buildroot}%{_unitdir}

# guestServer
%pre -n mtce-guestServer
%service_add_pre guestServer.service

# enable all services in systemd
%post -n mtce-guestServer
%service_add_post guestServer.service
systemctl enable guestServer.service

%preun -n mtce-guestServer
%service_del_preun guestServer.service

%postun -n mtce-guestServer
%service_del_postun guestServer.service
%insserv_cleanup

# guestAgent
%pre -n mtce-guestAgent
%service_add_pre guestAgent.service

%post -n mtce-guestAgent
%service_add_post guestAgent.service

%preun -n mtce-guestAgent
%service_del_preun guestAgent.service

%postun -n mtce-guestAgent
%service_del_postun guestAgent.service
%insserv_cleanup

%files -n mtce-guestAgent
%license LICENSE
%defattr(-,root,root,-)

# create mtc and its tmp dir
%dir %{_sysconfdir}/mtc
%dir %{_sysconfdir}/mtc/tmp

# config files - non-modifiable
%{_sysconfdir}/mtc/guestAgent.ini

%{_unitdir}/guestAgent.service
%{_sysconfdir}/logrotate.d/guestAgent.logrotate
/usr/lib/ocf/resource.d/platform/guestAgent

%{_sysconfdir}/init.d/guestAgent
%{local_bindir}/guestAgent

%{_prefix}/lib/ocf
%{_prefix}/lib/ocf/resource.d
%{_prefix}/lib/ocf/resource.d/platform
%config %{_sysconfdir}/logrotate.d/guestAgent.logrotate
%config %{_sysconfdir}/mtc/guestAgent.ini

%files -n mtce-guestServer
%license LICENSE
%defattr(-,root,root,-)

# create mtc and its tmp dir
%dir %{_sysconfdir}/mtc
%dir %{_sysconfdir}/mtc/tmp

# config files - non-modifiable
%{_sysconfdir}/mtc/guestServer.ini

%{_sysconfdir}/pmon.d/guestServer.conf
%{_sysconfdir}/logrotate.d/guestServer.logrotate
%{_unitdir}/guestServer.service

%{_sysconfdir}/init.d/guestServer
%{local_bindir}/guestServer

%{_sysconfdir}/pmon.d
%config %{_sysconfdir}/logrotate.d/guestServer.logrotate
%config %{_sysconfdir}/mtc/guestServer.ini
%config %{_sysconfdir}/pmon.d/guestServer.conf

%changelog
