Summary: Nova Compute API Proxy
Name: nova-api-proxy
Version: 1.0.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: System/Packages
URL: https://opendev.org/starlingx/nfv/
Source0: %{name}-%{version}.tar.gz

%define debug_package %{nil}

BuildRequires: python-setuptools
BuildRequires: python2-pip
Requires: python-eventlet
Requires: python2-Routes
Requires: python-webob
Requires: python-paste
BuildRequires: fdupes

%description
The Nova Compute API Proxy

%define local_bindir %{_bindir}
%define local_initddir %{_sysconfdir}/rc.d/init.d
%define pythonroot %{_libdir}/python2.7/site-packages
%define local_etc_systemd %{_sysconfdir}/systemd/system/
%define local_proxy_conf %{_sysconfdir}/proxy/

%prep
%setup -n %{name}-%{version}/%{name}

%build
%{__python} setup.py build

%install
%{__python} setup.py install --root=$RPM_BUILD_ROOT \
                             --install-lib=%{pythonroot} \
                             --prefix=%{_prefix} \
                             --install-data=%{_prefix}/share \
                             --single-version-externally-managed

install -d -m 755 %{buildroot}%{local_etc_systemd}
install -p -D -m 644 nova_api_proxy/scripts/api-proxy.service %{buildroot}%{local_etc_systemd}/api-proxy.service
install -d -m 755 %{buildroot}%{local_initddir}
install -p -D -m 755 nova_api_proxy/scripts/api-proxy %{buildroot}%{local_initddir}/api-proxy

install -d -m 755 %{buildroot}%{local_proxy_conf}
install -p -D -m 600 nova_api_proxy/nova-api-proxy.conf %{buildroot}%{local_proxy_conf}/nova-api-proxy.conf
install -p -D -m 600 nova_api_proxy/api-proxy-paste.ini %{buildroot}%{local_proxy_conf}/api-proxy-paste.ini

%fdupes %{buildroot}%{pythonroot}

%clean
rm -rf $RPM_BUILD_ROOT

# Note: Package name is nova-api-proxy but import is nova_api_proxy so can't
# use '%%{name}'.
%files
%defattr(-,root,root,-)
%dir %{_sysconfdir}/proxy
%dir %{_sysconfdir}/rc.d
%dir %{_sysconfdir}/rc.d/init.d
%dir %{_sysconfdir}/systemd
%dir %{_sysconfdir}/systemd/system
%dir %{_libdir}/python2.7/site-packages/api_proxy-1.0.0-py2.7.egg-info
%doc LICENSE
%{local_bindir}/*
%{local_initddir}/*
%{local_etc_systemd}/*
%config(noreplace) %{local_proxy_conf}/nova-api-proxy.conf
%{local_proxy_conf}/api-proxy-paste.ini
%dir %{pythonroot}/nova_api_proxy
%{pythonroot}/nova_api_proxy/*
%{pythonroot}/api_proxy-%{version}-py2.7.egg-info/*

%changelog
