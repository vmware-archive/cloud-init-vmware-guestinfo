#!/bin/sh

# Exit as soon as there is an unexpected error.
set -e

#
# usage: install.sh
#        curl -sSL https://raw.githubusercontent.com/vmware/cloud-init-vmware-guestinfo/master/install.sh | sh -
#

# The repository from which to fetch the cloud-init datasource and config files.
REPO_SLUG="${REPO_SLUG:-https://raw.githubusercontent.com/vmware/cloud-init-vmware-guestinfo}"

# The git reference to use. This can be a branch or tag name as well as a commit ID.
GIT_REF="${GIT_REF:-master}"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required" 1>&2
  exit 1
fi

if ! command -v python >/dev/null 2>&1 && \
   ! command -v python3 >/dev/null 2>&1; then
  echo "python 2 or 3 is required" 1>&2
  exit 1
fi

# PYTHON_VERSION may be 2 or 3 and indicates which version of Python
# is used by cloud-init. This variable is not set until PY_MOD_CLOUD_INIT
# is resolved.
PYTHON_VERSION=
get_py_mod_dir() {
  _script='import os; import '"${1-}"'; print(os.path.dirname('"${1-}"'.__file__));'
  case "${PYTHON_VERSION}" in
  2)
    python -c ''"${_script}"'' 2>/dev/null || echo ""
    ;;
  3)
    python3 -c ''"${_script}"'' 2>/dev/null || echo ""
    ;;
  *)
    { python3 -c ''"${_script}"'' || python -c ''"${_script}"'' || echo ""; } 2>/dev/null
    ;;
  esac
}

# PY_MOD_CLOUD_INIT is set to the the "cloudinit" directory in either
# the Python2 or Python3 lib directory. This is also used to determine
# which version of Python is repsonsible for running cloud-init.
PY_MOD_CLOUD_INIT="$(get_py_mod_dir cloudinit)"
if [ -z "${PY_MOD_CLOUD_INIT}" ]; then
  echo "cloudinit is required" 1>&2
  exit 1
fi
if echo "${PY_MOD_CLOUD_INIT}" | grep -q python2; then
  PYTHON_VERSION=2
else
  PYTHON_VERSION=3
fi
echo "using python ${PYTHON_VERSION}"

# The following modules are required:
#   * netifaces
# If a module is already installed then it is assumed to be compatible.
# Otherwise an attempt is made to install the module with pip.
if [ -z "$(get_py_mod_dir netifaces)" ]; then
  echo "installing requirements"
  if [ -z "$(get_py_mod_dir pip)" ]; then
    echo "pip is required" 1>&2
    exit 1
  fi
  _requirements="requirements.txt"
  if [ ! -f "${_requirements}" ]; then
    _requirements="$(mktemp)"
    curl -sSL -o "${_requirements}" "${REPO_SLUG}/${GIT_REF}/requirements.txt"
  fi
  case "${PYTHON_VERSION}" in
  2)
    python -m pip install -r "${_requirements}"
    ;;
  3)
    python3 -m pip install -r "${_requirements}"
    ;;
  esac
fi

# Download the cloud init datasource into the cloud-init's "sources" directory.
echo "installing datasource"
curl -sSL -o "${PY_MOD_CLOUD_INIT}/sources/DataSourceVMwareGuestInfo.py" \
  "${REPO_SLUG}/${GIT_REF}/DataSourceVMwareGuestInfo.py"

# Make sure that the datasource can execute without error on this host.
echo "validating datasource"
case "${PYTHON_VERSION}" in
2)
  python "${PY_MOD_CLOUD_INIT}/sources/DataSourceVMwareGuestInfo.py" 1>/dev/null
  ;;
3)
  python3 "${PY_MOD_CLOUD_INIT}/sources/DataSourceVMwareGuestInfo.py" 1>/dev/null
  ;;
esac

# Add the configuration file that tells cloud-init what datasource to use.
echo "installing config"
mkdir -p /etc/cloud/cloud.cfg.d
curl -sSL -o /etc/cloud/cloud.cfg.d/99-DataSourceVMwareGuestInfo.cfg \
  "${REPO_SLUG}/${GIT_REF}/99-DataSourceVMwareGuestInfo.cfg"

# Download program used by ds-identify to determine whether or not the
# VMwareGuestInfo datasource is useable.
echo "installing dscheck"
curl -sSL -o "/usr/bin/dscheck_VMwareGuestInfo" \
  "${REPO_SLUG}/${GIT_REF}/dscheck_VMwareGuestInfo.sh"
chmod 0755 "/usr/bin/dscheck_VMwareGuestInfo"

echo "So long, and thanks for all the fish."
