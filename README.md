# CentOS Cloud-Init Datasource for VMware VMX Guestinfo
This project uses Docker to build an RPM for CentOS that provides a
cloud-init datasource for VMware's VMX Guestinfo interface.

## Getting Started
Docker is required to build the RPM. Once Docker is installed simply run:

```shell
$ make
```

The RPM is created at `rpmbuild/RPMS/noarch/cloud-init-vmx-guestinfo-VERSION-RELEASE.noarch.rpm`.

## Installation
Either the `rpm` or `yum` tools can be used to install the RPM on CentOS.

```shell
$ yum install https://s3-us-west-2.amazonaws.com/cnx.vmware/cicd/centos/cloud-init-vmx-guestinfo-1.0.4-0.noarch.rpm
```

The above command will also install the required `cloud-init` dependency.

## Creating a cloud-config file
The first step to use the data source is to create a cloud config file:

```yaml
#cloud-config

users:
  - default
  - name: akutz
    primary_group: akutz
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: sudo, wheel
    ssh_import_id: None
    lock_passwd: true
    ssh_authorized_keys:
      - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDE0c5FczvcGSh/tG4iw+Fhfi/O5/EvUM/96js65tly4++YTXK1d9jcznPS5ruDlbIZ30oveCBd3kT8LLVFwzh6hepYTf0YmCTpF4eDunyqmpCXDvVscQYRXyasEm5olGmVe05RrCJSeSShAeptv4ueIn40kZKOghinGWLDSZG4+FFfgrmcMCpx5YSCtX2gvnEYZJr0czt4rxOZuuP7PkJKgC/mt2PcPjooeX00vAj81jjU2f3XKrjjz2u2+KIt9eba+vOQ6HiC8c2IzRkUAJ5i1atLy8RIbejo23+0P4N2jjk17QySFOVHwPBDTYb0/0M/4ideeU74EN/CgVsvO6JrLsPBR4dojkV5qNbMNxIVv5cUwIy2ThlLgqpNCeFIDLCWNZEFKlEuNeSQ2mPtIO7ETxEL2Cz5y/7AIuildzYMc6wi2bofRC8HmQ7rMXRWdwLKWsR0L7SKjHblIwarxOGqLnUI+k2E71YoP7SZSlxaKi17pqkr0OMCF+kKqvcvHAQuwGqyumTEWOlH6TCx1dSPrW+pVCZSHSJtSTfDW2uzL6y8k10MT06+pVunSrWo5LHAXcS91htHV1M1UrH/tZKSpjYtjMb5+RonfhaFRNzvj7cCE1f3Kp8UVqAdcGBTtReoE8eRUT63qIxjw03a7VwAyB2w+9cu1R9/vAo8SBeRqw== sakutz@gmail.com
```

## Assigning the cloud-config data to the VM's Guestinfo
Please note that this step requires that the VM be powered off.

Once the cloud config file has been created, use the 
[`govc`](https://github.com/vmware/govmomi/blob/master/govc/USAGE.md#vmchange)
tool's `vm.change` command to set the appropriate keys on the powered-off VM:

```shell
$ govc vm.change -vm $VM -e guestinfo.userdata=$(cat cloud-config.yaml | gzip -9 | base64)
$ govc vm.change -vm $VM -e guestinfo.userdata.encoding=gzip+base64
```

## Using the cloud-init VMX Guestinfo datasource
Power the VM back on. If all went according to plan, the CentOS box has been
locked down to SSH access only for the user defined in the above cloud-config
YAML file.

## Conclusion
To learn more about how to use cloud-init with CentOS, please see the cloud-init
[documentation](https://cloudinit.readthedocs.io/en/latest/index.html) for more 
examples and reference information for the cloud-config files.
