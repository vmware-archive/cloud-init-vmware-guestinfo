#
# spec file for package cloud-init-vmx-guestinfo
#

#################################################################################
# common
#################################################################################
Name:           cloud-init-vmx-guestinfo
Version:        1.0.4
Release:        0
Summary:        A cloud-init datasource that uses VMX Guestinfo
License:        Apache2
Requires:       cloud-init
Group:          Applications/System
BuildArch:      noarch

#################################################################################
# specific
#################################################################################
%description
A cloud-init datasource that uses VMX Guestinfo

%prep

%build

%install
mkdir -p %{buildroot}/
cp -r ./* %buildroot/
exit 0

%clean

%files
%defattr(0644, root,root, 0755)
/etc/cloud/cloud.cfg.d/10_vmx_guestinfo.cfg
/usr/lib/python2.7/site-packages/cloudinit/sources/DataSourceVmxGuestinfo.py
