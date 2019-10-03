Summary: Nova Compute API Proxy
Name: nova-api-proxy
Version: 1.0.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: System/Packages
URL: https://opendev.org/starlingx/nfv/
Source0: %{name}-%{version}.tar.gz

%define debug_package %{nil}

BuildRequires: fdupes
BuildRequires: python-setuptools
BuildRequires: python2-pip
Requires: python-eventlet
Requires: python2-Routes
Requires: python-webob
Requires: python-paste

%description
The Nova Compute API Proxy

%define local_initddir %{_sysconfdir}/rc.d/init.d
%define pythonroot %{_libdir}/python2.7/site-packages
%define local_etc_systemd %{_sysconfdir}/systemd/system/
%define local_proxy_conf %{_sysconfdir}/proxy/

%prep
%setup -n %{name}-%{version}/%{name}

%build
%{__python} setup.py build

%install
%{__python} setup.py install --root=%{buildroot} \
                             --install-lib=%{pythonroot} \
                             --prefix=%{_prefix} \
                             --install-data=%{_prefix}/share \
                             --single-version-externally-managed

install -d -m 755 %{buildroot}%{local_etc_systemd}
install -d -m 755 %{buildroot}%{_sysconfdir}/rc.d/init.d
install -d -m 755 %{buildroot}%{local_proxy_conf}

install -p -D -m 644 nova_api_proxy/scripts/api-proxy.service \
        %{buildroot}%{_unitdir}/api-proxy.service
install -p -D -m 755 nova_api_proxy/scripts/api-proxy \
        %{buildroot}%{_sysconfdir}/rc.d/init.d/api-proxy
install -p -D -m 600 nova_api_proxy/nova-api-proxy.conf \
        %{buildroot}%{local_proxy_conf}/nova-api-proxy.conf
install -p -D -m 600 nova_api_proxy/api-proxy-paste.ini \
        %{buildroot}%{local_proxy_conf}/api-proxy-paste.ini

%fdupes %{buildroot}%{pythonroot}

%clean
rm -rf %{buildroot}

%pre
%service_add_pre api-proxy.service

%preun
%service_del_preun api-proxy.service

%post
%service_add_post api-proxy.service
%set_permissions %{pythonroot}/nova_api_proxy/api_proxy.py

%postun
%service_del_postun api-proxy.service

# Note: Package name is nova-api-proxy but import is nova_api_proxy so can't
# use '%%{name}'.
%files
%defattr(-,root,root,-)
%dir %{_sysconfdir}/rc.d
%dir %{_sysconfdir}/rc.d/init.d
%dir %{_sysconfdir}/proxy
%dir %{pythonroot}/api_proxy-%{version}-py2.7.egg-info
%dir %{pythonroot}/nova_api_proxy

%{_bindir}/nova-api-proxy
%{_unitdir}/api-proxy.service
%{_sysconfdir}/rc.d/init.d/api-proxy
%{pythonroot}/nova_api_proxy/*
%{pythonroot}/api_proxy-%{version}-py2.7.egg-info/*
%config(noreplace) %{_sysconfdir}/proxy/nova-api-proxy.conf
%config %{_sysconfdir}/proxy/api-proxy-paste.ini
%license LICENSE

%changelog
