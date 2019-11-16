#
# spec file for package cloud-init-vmware-guestinfo
#

#################################################################################
# common
#################################################################################
Name:           cloud-init-vmware-guestinfo
Version:        1.1.0
Release:        1.el8
Summary:        A cloud-init datasource that uses VMware GuestInfo
License:        Apache2
Requires:       cloud-init python3-netifaces
Group:          Applications/System
BuildArch:      noarch

#################################################################################
# specific
#################################################################################
%description
A cloud-init datasource that uses VMware GuestInfo

%prep

%build

%install
mkdir -p %{buildroot}/etc/cloud/cloud.cfg.d
mkdir -p %{buildroot}/usr/lib/python3.6/site-packages/cloudinit/sources
cp 99-DataSourceVMwareGuestInfo.cfg %{buildroot}/etc/cloud/cloud.cfg.d/99-DataSourceVMwareGuestInfo.cfg
cp DataSourceVMwareGuestInfo.py %{buildroot}/usr/lib/python3.6/site-packages/cloudinit/sources/DataSourceVMwareGuestInfo.py

%clean

%files
%defattr(0644, root,root, 0755)
/etc/cloud/cloud.cfg.d/99-DataSourceVMwareGuestInfo.cfg
/usr/lib/python3.6/site-packages/cloudinit/sources/DataSourceVMwareGuestInfo.py
/usr/lib/python3.6/site-packages/cloudinit/sources/__pycache__/DataSourceVMwareGuestInfo.*.pyc
