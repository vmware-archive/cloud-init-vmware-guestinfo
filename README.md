# Cloud-Init Datasource for VMware GuestInfo

This project provides a cloud-init datasource for pulling meta, user, and vendor data from VMware vSphere's GuestInfo [interface](https://github.com/vmware/govmomi/blob/master/govc/USAGE.md#vmchange).

## Installation

There are multiple methods of installing the data source.

### Installing on RHEL/CentOS 7

There is an RPM available for installing on RedHat/CentOS:

```shell
yum install https://github.com/vmware/cloud-init-vmware-guestinfo/releases/download/v1.1.0/cloud-init-vmware-guestinfo-1.1.0-1.el7.noarch.rpm
```

### Installing on other Linux distributions

The VMware GuestInfo datasource can be installed on any Linux distribution where cloud-init is already present. To do so, simply execute the following:

```shell
curl -sSL https://raw.githubusercontent.com/vmware/cloud-init-vmware-guestinfo/master/install.sh | sh -
```

## Configuration

The data source is configured by setting `guestinfo` properties on a VM's `extraconfig` data or a customizable vApp's `properties` data.

| Property | Description |
|----------|-------------|
| `guestinfo.metadata` | A JSON string containing the cloud-init metadata. |
| `guestinfo.metadata.encoding` | The encoding type for `guestinfo.metadata`. |
| `guestinfo.userdata` | A YAML document containing the cloud-init user data. |
| `guestinfo.userdata.encoding` | The encoding type for `guestinfo.userdata`. |
| `guestinfo.vendordata` | A YAML document containing the cloud-init vendor data. |
| `guestinfo.vendordata.encoding` | The encoding type for `guestinfo.vendordata`. |

All `guestinfo.*.encoding` property values may be set to `base64` or `gzip+base64`.

## Walkthrough

The following series of steps is a demonstration on how to configure a VM with cloud-init and the VMX GuestInfo datasource.

### Create a metadata file

First, create the metadata file for the VM. Save the following YAML to a file named `metadata.yaml`:

```yaml
instance-id: cloud-vm
local-hostname: cloud-vm
network:
  version: 2
  ethernets:
    nics:
      match:
        name: ens*
      dhcp4: yes
```

### Create a userdata file

Finally, create the userdata file `userdata.yaml`:

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

### Assigning the userdate data to the VM's GuestInfo

Please note that this step requires that the VM be powered off. All of the commands below use the VMware CLI tool, [`govc`](https://github.com/vmware/govmomi/blob/master/govc).

Go ahead and assign the path to the VM to the environment variable `VM`:

```shell
export VM="/inventory/path/to/the/vm"
```

Next, power off the VM:

```shell
govc vm.power -off "${VM}"
```

Export the environment variables that contain the cloud-init metadata and userdata:

```shell
export METADATA=$(gzip -c9 <metadata.yaml | { base64 -w0 2>/dev/null || base64; }) \
       USERDATA=$(gzip -c9 <userdata.yaml | { base64 -w0 2>/dev/null || base64; })
```

Assign the metadata and userdate to the VM's extra configuration dictionary, `guestinfo`:

```shell
govc vm.change -vm "${VM}" \
  -e guestinfo.metadata="${METADATA}" \
  -e guestinfo.metadata.encoding="gzip+base64" \
  -e guestinfo.userdata="${USERDATA}" \
  -e guestinfo.userdata.encoding="gzip+base64"
```

Please note the above commands include specifying the encoding for the properties. This is important as it informs the datasource how to decode the data for cloud-init. Valid values for `metadata.encoding` and `userdata.encoding` include:

* `base64`
* `gzip+base64`

### Using the cloud-init VMX GuestInfo datasource

Power the VM back on.

```shell
govc vm.power -vm "${VM}" -on
```

If all went according to plan, the CentOS box is:

* Locked down, allowing SSH access only for the user in the userdata
* Configured for a dynamic IP address via DHCP
* Has a hostname of `cloud-vm`

## Examples

This section reviews common configurations:

### Setting the hostname

The hostname is set by way of the metadata key `local-hostname`.

### Setting the instance ID

The instance ID may be set by way of the metadata key `instance-id`. However, if this value is absent then then the instance ID is read from the file `/sys/class/dmi/id/product_uuid`.

### Providing public SSH keys

The public SSH keys may be set by way of the metadata key `public-keys-data`. Each newline-terminated string will be interpreted as a separate SSH public key, which will be placed in distro's default user's `~/.ssh/authorized_keys`. If the value is empty or absent, then nothing will be written to `~/.ssh/authorized_keys`.

### Configuring the network

The network is configured by setting the metadata key `network` with a value consistent with Network Config Versions [1](http://bit.ly/cloudinit-net-conf-v1) or [2](http://bit.ly/cloudinit-net-conf-v2), depending on the Linux distro's version of cloud-init.

The metadata key `network.encoding` may be used to indicate the format of the metadata key "network". Valid encodings are `base64` and `gzip+base64`.

### Cleaning up the guestinfo keys

Sometimes the cloud-init userdata might contain sensitive information, and it may be desirable to have the `guestinfo.userdata` key (or other guestinfo keys) cleared as soon as its data is read by the datasource. This is possible by adding the following to the metadata:

```yaml
cleanup-guestinfo:
- userdata
- vendordata
```

When the above snippet is added to the metadata, the datasource will iterate over the elements in the `cleanup-guestinfo` array and clear each of the keys. For example, the above snippet will cause the following commands to be executed:

```shell
vmware-rpctool "info-set guestinfo.userdata ---"
vmware-rpctool "info-set guestinfo.userdata.encoding  "
vmware-rpctool "info-set guestinfo.vendordata ---"
vmware-rpctool "info-set guestinfo.vendordata.encoding  "
```

Please note that keys are set to the valid YAML string `---` as it is not possible remove an existing key from the guestinfo key-space. A key's analogous encoding property will be set to a single white-space character, causing the datasource to treat the actual key value as plain-text, thereby loading it as an empty YAML doc (hence the aforementioned `---`).

### Reading the local IP addresses

This datasource automatically discovers the local IPv4 and IPv6 addresses for a guest operating system based on the default routes. However, when inspecting a VM externally, it's not possible to know what the _default_ IP address is for the guest OS. That's why this datasource sets the discovered, local IPv4 and IPv6 addresses back in the guestinfo namespace as the following keys:

* `guestinfo.local-ipv4`
* `guestinfo.local-ipv6`

It is possible that a host may not have any default, local IP addresses. It's also possible the reported, local addresses are link-local addresses. But these two keys may be used to discover what this datasource determined were the local IPv4 and IPv6 addresses for a host.

### Waiting on the network

Sometimes cloud-init may bring up the network, but it will not finish coming online before the datasource's `setup` function is called, resulting in an `/var/run/cloud-init/instance-data.json` file that does not have the correct network information. It is possible to instruct the datasource to wait until an IPv4 or IPv6 address is available before writing the instance data with the following metadata properties:

```yaml
wait-on-network:
  ipv4: true
  ipv6: true
```

If either of the above values are true, then the datasource will sleep for a second, check the network status, and repeat until one or both addresses from the specified families are available.



## Building the RPM

Building the RPM locally is handled via Docker. Simple execute the following command:

```shell
make rpm
```

The resulting RPMs are located in `rpmbuild/$OS/RPMS/noarch/`. The list of supported `$OS` platforms are:

* el7 (RHEL/CentOS 7)

## Conclusion

To learn more about how to use cloud-init with CentOS, please see the cloud-init [documentation](https://cloudinit.readthedocs.io/en/latest/index.html) for more examples and reference information for the cloud-config files.
