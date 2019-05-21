#!/bin/sh

#
# usage: install.sh
#        curl -sSL https://raw.githubusercontent.com/akutz/cloud-init-vmware-guestinfo/master/install.sh | sh -
#

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required" 1>&2
  exit 1
fi

# The script to lookup the path to the cloud-init's datasource directory, "sources".
PY_SCRIPT='import os; from cloudinit import sources; print(os.path.dirname(sources.__file__));'

# Get the path to the cloud-init installation's datasource directory.
CLOUD_INIT_SOURCES=$(python -c ''"${PY_SCRIPT}"'' 2>/dev/null || \
  python3 -c ''"${PY_SCRIPT}"'' 2>/dev/null) ||
  { exit_code="${?}"; echo "failed to find python runtime" 1>&2; exit "${exit_code}"; }

# If no "sources" directory was located then it's likely cloud-init is not installed.
[ -z "${CLOUD_INIT_SOURCES}" ] && echo "cloud-init not found" 1>&2 && exit 1

# The repository from which to fetch the cloud-init datasource and config files.
REPO_SLUG="${REPO_SLUG:-https://raw.githubusercontent.com/akutz/cloud-init-vmware-guestinfo}"

# The git reference to use. This can be a branch or tag name as well as a commit ID.
GIT_REF="${GIT_REF:-master}"

# Download the cloud init datasource into the cloud-init's "sources" directory.
curl -sSL -o "${CLOUD_INIT_SOURCES}/DataSourceVMwareGuestInfo.py" \
  "${REPO_SLUG}/${GIT_REF}/DataSourceVMwareGuestInfo.py"

# Add the configuration file that tells cloud-init what datasource to use.
mkdir -p /etc/cloud/cloud.cfg.d
curl -sSL -o /etc/cloud/cloud.cfg.d/99-DataSourceVMwareGuestInfo.cfg \
  "${REPO_SLUG}/${GIT_REF}/99-DataSourceVMwareGuestInfo.cfg"

echo "So long, and thanks for all the fish."
