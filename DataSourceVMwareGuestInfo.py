# vi: ts=4 expandtab
#
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
import os
import base64
import zlib
import json

from cloudinit import log as logging
from cloudinit import sources
from cloudinit import util
from cloudinit import safeyaml

from distutils.spawn import find_executable

LOG = logging.getLogger(__name__)

# This cloud-init datasource was designed for use with CentOS 7,
# which uses cloud-init 0.7.9. However, this datasource should
# work with any Linux distribution for which cloud-init is 
# avaialble.
#
# The documentation for cloud-init 0.7.9's datasource is 
# available at http://bit.ly/cloudinit-datasource-0-7-9. The
# current documentation for cloud-init is found at
# https://cloudinit.readthedocs.io/en/latest/.
#
# Setting the hostname:
#     The hostname is set by way of the metadata key "local-hostname".
#
# Setting the instance ID:
#     The instance ID may be set by way of the metadata key "instance-id".
#     However, if this value is absent then then the instance ID is
#     read from the file /sys/class/dmi/id/product_uuid.
#
# Configuring the network:
#     The network is configured by setting the metadata key "network"
#     with a value consistent with Network Config Versions 1 or 2,
#     depending on the Linux distro's version of cloud-init:
#
#         Network Config Version 1 - http://bit.ly/cloudinit-net-conf-v1
#         Network Config Version 2 - http://bit.ly/cloudinit-net-conf-v2
#
#     For example, CentOS 7's official cloud-init package is version
#     0.7.9 and does not support Network Config Version 2. However,
#     this datasource still supports supplying Network Config Version 2
#     data as long as the Linux distro's cloud-init package is new
#     enough to parse the data.
#
#     The metadata key "network.encoding" may be used to indicate the
#     format of the metadata key "network". Valid encodings are base64
#     and gzip+base64.
class DataSourceVMwareGuestInfo(sources.DataSource):
    def __init__(self, sys_cfg, distro, paths, ud_proc=None):
        sources.DataSource.__init__(self, sys_cfg, distro, paths, ud_proc)
        self.vmtoolsd = find_executable("vmtoolsd")
        if not self.vmtoolsd:
            LOG.error("Failed to find vmtoolsd")

    def get_data(self):
        if not self.vmtoolsd:
            LOG.error("vmtoolsd is required to fetch guestinfo value")
            return False

        # Get the JSON metadata. Can be plain-text, base64, or gzip+base64.
        metadata = self._get_encoded_guestinfo_data('metadata')
        if metadata:
            self.metadata = json.loads(metadata)

        # Get the YAML userdata. Can be plain-text, base64, or gzip+base64.
        self.userdata_raw = self._get_encoded_guestinfo_data('userdata')

        # Get the YAML vendordata. Can be plain-text, base64, or gzip+base64.
        self.vendordata_raw = self._get_encoded_guestinfo_data('vendordata')

        return True

    @property
    def network_config(self):
        # Pull the network configuration out of the metadata.
        if self.metadata and 'network' in self.metadata:
            data = self._get_encoded_metadata('network')
            if data:
                # Load the YAML-formatted network data into an object
                # and return it.
                net_config = safeyaml.load(data)
                LOG.debug("Loaded network config: %s", net_config)
                return net_config
        return None

    def get_instance_id(self):
        # Pull the instance ID out of the metadata if present. Otherwise
        # read the file /sys/class/dmi/id/product_uuid for the instance ID.
        if self.metadata and 'instance-id' in self.metadata:
            return self.metadata['instance-id']
        with open('/sys/class/dmi/id/product_uuid', 'r') as id_file:
            return str(id_file.read()).rstrip()

    def _get_encoded_guestinfo_data(self, key):
        data = self._get_guestinfo_value(key)
        if not data:
            return None
        enc_type = self._get_guestinfo_value(key + '.encoding')
        return self._get_encoded_data('guestinfo.' + key, enc_type, data)

    def _get_encoded_metadata(self, key):
        if not self.metadata or not key in self.metadata:
            return None
        data = self.metadata[key]
        enc_type = self.metadata.get(key + '.encoding')
        return self._get_encoded_data('metadata.' + key, enc_type, data)

    def _get_encoded_data(self, key, enc_type, data):
        '''
        The _get_encoded_data would always return a str
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
        rawdata = self._get_encoded_data_raw(key, enc_type, data)
        if type(rawdata) == bytes:
            return rawdata.decode('utf-8')
        return rawdata

    def _get_encoded_data_raw(self, key, enc_type, data):
        LOG.debug("Getting encoded data for key=%s, enc=%s", key, enc_type)
        if enc_type == "gzip+base64" or enc_type == "gz+b64":
            LOG.debug("Decoding %s format %s", enc_type, key)
            return zlib.decompress(base64.b64decode(data), zlib.MAX_WBITS | 16)
        elif enc_type == "base64" or enc_type == "b64":
            LOG.debug("Decoding %s format %s", enc_type, key)
            return base64.b64decode(data)
        else:
            LOG.debug("Plain-text data %s", key)
            return data

    def _get_guestinfo_value(self, key):
        NOVAL = "No value found"
        LOG.debug("Getting guestinfo value for key %s", key)
        try:
            (stdout, stderr) = util.subp([self.vmtoolsd, "--cmd", "info-get guestinfo." + key])
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
                util.logexc(LOG,"Failed to get guestinfo value for key %s: %s", key, error)
        except Exception:
            util.logexc(LOG,"Unexpected error while trying to get guestinfo value for key %s", key)
        return None

def get_datasource_list(depends):
    """
    Return a list of data sources that match this set of dependencies
    """
    return [DataSourceVMwareGuestInfo]
