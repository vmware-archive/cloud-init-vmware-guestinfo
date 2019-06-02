# Cloud-Init Datasource for VMware Guestinfo
#
# Copyright (c) 2018 VMware, Inc. All Rights Reserved.
#
# This product is licensed to you under the Apache 2.0 license (the "License").
# You may not use this product except in compliance with the Apache 2.0 License.
#
# This product may include a number of subcomponents with separate copyright
# notices and license terms. Your use of these subcomponents is subject to the
# terms and conditions of the subcomponent's license, as noted in the LICENSE
# file.
#
# Authors: Anish Swaminathan <anishs@vmware.com>
#          Andrew Kutz <akutz@vmware.com>
#

'''
A cloud init datasource for VMware GuestInfo.
'''

import collections
import base64
import zlib
import json
from distutils.spawn import find_executable

from cloudinit import log as logging
from cloudinit import sources
from cloudinit import util
from cloudinit import safeyaml

LOG = logging.getLogger(__name__)
NOVAL = "No value found"
VMTOOLSD = find_executable("vmtoolsd")


class NetworkConfigError(Exception):
    '''
    NetworkConfigError is raised when there is an issue getting or
    applying network configuration.
    '''
    pass


class DataSourceVMwareGuestInfo(sources.DataSource):
    '''
    This cloud-init datasource was designed for use with CentOS 7,
    which uses cloud-init 0.7.9. However, this datasource should
    work with any Linux distribution for which cloud-init is
    avaialble.

    The documentation for cloud-init 0.7.9's datasource is
    available at http://bit.ly/cloudinit-datasource-0-7-9. The
    current documentation for cloud-init is found at
    https://cloudinit.readthedocs.io/en/latest/.

    Setting the hostname:
        The hostname is set by way of the metadata key "local-hostname".

    Setting the instance ID:
        The instance ID may be set by way of the metadata key "instance-id".
        However, if this value is absent then then the instance ID is
        read from the file /sys/class/dmi/id/product_uuid.

    Configuring the network:
        The network is configured by setting the metadata key "network"
        with a value consistent with Network Config Versions 1 or 2,
        depending on the Linux distro's version of cloud-init:

            Network Config Version 1 - http://bit.ly/cloudinit-net-conf-v1
            Network Config Version 2 - http://bit.ly/cloudinit-net-conf-v2

        For example, CentOS 7's official cloud-init package is version
        0.7.9 and does not support Network Config Version 2. However,
        this datasource still supports supplying Network Config Version 2
        data as long as the Linux distro's cloud-init package is new
        enough to parse the data.

        The metadata key "network.encoding" may be used to indicate the
        format of the metadata key "network". Valid encodings are base64
        and gzip+base64.
    '''

    dsname = 'VMwareGuestInfo'

    def __init__(self, sys_cfg, distro, paths, ud_proc=None):
        sources.DataSource.__init__(self, sys_cfg, distro, paths, ud_proc)
        if not VMTOOLSD:
            LOG.error("Failed to find vmtoolsd")

    def get_data(self):
        """
        This method should really be _get_data in accordance with the most
        recent versions of cloud-init. However, because the datasource
        supports as far back as cloud-init 0.7.9, get_data is still used.

        Because of this the method attempts to do some of the same things
        that the get_data functions in newer versions of cloud-init do,
        such as calling persist_instance_data.
        """
        if not VMTOOLSD:
            LOG.error("vmtoolsd is required to fetch guestinfo value")
            return False

        # Get the metadata.
        self.metadata = load_metadata()

        # Get the user data.
        self.userdata_raw = guestinfo('userdata')

        # Get the vendor data.
        self.vendordata_raw = guestinfo('vendordata')

        return True

    def setup(self, is_new_instance):
        """setup(is_new_instance)

        This is called before user-data and vendor-data have been processed.

        Unless the datasource has set mode to 'local', then networking
        per 'fallback' or per 'network_config' will have been written and
        brought up the OS at this point.
        """

        # Set the hostname.
        hostname = self.metadata.get('local-hostname')
        if hostname:
            self.distro.set_hostname(hostname)
            LOG.info("set hostname %s", hostname)

        # Update the metadata with the actual host name and actual network
        # interface information.
        host_info = get_host_info()
        LOG.info("got host-info: %s", host_info)
        hostname = host_info.get('local-hostname', hostname)
        self.metadata['local-hostname'] = hostname
        interfaces = host_info['network']['interfaces']
        self.metadata['network']['interfaces'] = interfaces

        # Persist the instance data for versions of cloud-init that support
        # doing so. This occurs here rather than in the get_data call in
        # order to ensure that the network interfaces are up and can be
        # persisted with the metadata.
        try:
            self.persist_instance_data()
        except AttributeError:
            pass

    @property
    def network_config(self):
        if 'network' in self.metadata:
            LOG.debug("using metadata network config")
        else:
            LOG.debug("using fallback network config")
            self.metadata['network'] = {
                'config': self.distro.generate_fallback_config(),
            }
        return self.metadata['network']['config']

    def get_instance_id(self):
        # Pull the instance ID out of the metadata if present. Otherwise
        # read the file /sys/class/dmi/id/product_uuid for the instance ID.
        if self.metadata and 'instance-id' in self.metadata:
            return self.metadata['instance-id']
        with open('/sys/class/dmi/id/product_uuid', 'r') as id_file:
            self.metadata['instance-id'] = str(id_file.read()).rstrip()
            return self.metadata['instance-id']


def decode(key, enc_type, data):
    '''
    decode returns the decoded string value of data
    key is a string used to identify the data being decoded in log messages
    ----
    In py 2.7:
    json.loads method takes string as input
    zlib.decompress takes and returns a string
    base64.b64decode takes and returns a string
    -----
    In py 3.6 and newer:
    json.loads method takes bytes or string as input
    zlib.decompress takes and returns a bytes
    base64.b64decode takes bytes or string and returns bytes
    -----
    In py > 3, < 3.6:
    json.loads method takes string as input
    zlib.decompress takes and returns a bytes
    base64.b64decode takes bytes or string and returns bytes
    -----
    Given the above conditions the output from zlib.decompress and
    base64.b64decode would be bytes with newer python and str in older
    version. Thus we would covert the output to str before returning
    '''
    LOG.debug("Getting encoded data for key=%s, enc=%s", key, enc_type)

    raw_data = None
    if enc_type == "gzip+base64" or enc_type == "gz+b64":
        LOG.debug("Decoding %s format %s", enc_type, key)
        raw_data = zlib.decompress(base64.b64decode(data), zlib.MAX_WBITS | 16)
    elif enc_type == "base64" or enc_type == "b64":
        LOG.debug("Decoding %s format %s", enc_type, key)
        raw_data = base64.b64decode(data)
    else:
        LOG.debug("Plain-text data %s", key)
        raw_data = data

    if isinstance(raw_data, bytes):
        return raw_data.decode('utf-8')
    return raw_data


def get_guestinfo_value(key):
    '''
    Returns a guestinfo value for the specified key.
    '''
    LOG.debug("Getting guestinfo value for key %s", key)
    try:
        (stdout, stderr) = util.subp(
            [VMTOOLSD, "--cmd", "info-get guestinfo." + key])
        if stderr == NOVAL:
            LOG.debug("No value found for key %s", key)
        elif not stdout:
            LOG.error("Failed to get guestinfo value for key %s", key)
        else:
            return stdout.rstrip()
    except util.ProcessExecutionError as error:
        if error.stderr == NOVAL:
            LOG.debug("No value found for key %s", key)
        else:
            util.logexc(
                LOG, "Failed to get guestinfo value for key %s: %s", key, error)
    except Exception:
        util.logexc(
            LOG, "Unexpected error while trying to get guestinfo value for key %s", key)
    return None


def guestinfo(key):
    '''
    guestinfo returns the guestinfo value for the provided key, decoding
    the value when required
    '''
    data = get_guestinfo_value(key)
    if not data:
        return None
    enc_type = get_guestinfo_value(key + '.encoding')
    return decode('guestinfo.' + key, enc_type, data)


def load(data):
    '''
    load first attempts to unmarshal the provided data as JSON, and if
    that fails then attempts to unmarshal the data as YAML. If data is
    None then a new dictionary is returned.
    '''
    if not data:
        return {}
    try:
        return json.loads(data)
    except:
        return safeyaml.load(data)


def load_metadata():
    '''
    load_metadata loads the metadata from the guestinfo data, optionally
    decoding the network config when required
    '''
    data = load(guestinfo('metadata'))

    network = None
    if 'network' in data:
        network = data['network']
        del data['network']

    network_enc = None
    if 'network.encoding' in data:
        network_enc = data['network.encoding']
        del data['network.encoding']

    if network:
        if not isinstance(network, collections.Mapping):
            LOG.debug("decoding network data: %s", network)
            dec_net = decode('metadata.network', network_enc, network)
            network = load(dec_net)
        if 'config' not in network:
            raise NetworkConfigError("missing 'config' key")
        data['network'] = network

    return data


def get_datasource_list(depends):
    '''
    Return a list of data sources that match this set of dependencies
    '''
    return [DataSourceVMwareGuestInfo]


def get_host_info():
    '''
    Returns host information such as the host name and network interfaces.
    '''
    import netifaces
    import socket

    host_info = {
        'network': {
            'interfaces': {
                'by-mac': collections.OrderedDict(),
                'by-ip4': collections.OrderedDict(),
                'by-ip6': collections.OrderedDict(),
            },
        },
    }

    hostname = socket.getfqdn()
    if hostname:
        host_info['local-hostname'] = hostname

    by_mac = host_info['network']['interfaces']['by-mac']
    by_ip4 = host_info['network']['interfaces']['by-ip4']
    by_ip6 = host_info['network']['interfaces']['by-ip6']

    ifaces = netifaces.interfaces()
    for dev_name in ifaces:
        addr_fams = netifaces.ifaddresses(dev_name)
        af_link = addr_fams.get(netifaces.AF_LINK)
        af_inet = addr_fams.get(netifaces.AF_INET)
        af_inet6 = addr_fams.get(netifaces.AF_INET6)

        mac = None
        if af_link and 'addr' in af_link[0]:
            mac = af_link[0]['addr']

        # Do not bother recording localhost
        if mac == "00:00:00:00:00:00":
            continue

        if mac and (af_inet or af_inet6):
            key = mac
            val = {}
            if af_inet:
                val["ip4"] = af_inet
            if af_inet6:
                val["ip6"] = af_inet6
            by_mac[key] = val

        if af_inet:
            for ip_info in af_inet:
                key = ip_info['addr']
                val = ip_info.copy()
                del val['addr']
                if mac:
                    val['mac'] = mac
                by_ip4[key] = val

        if af_inet6:
            for ip_info in af_inet6:
                key = ip_info['addr']
                val = ip_info.copy()
                del val['addr']
                if mac:
                    val['mac'] = mac
                by_ip6[key] = val

    return host_info


if __name__ == "__main__":
    print util.json_dumps(get_host_info())

# vi: ts=4 expandtab
