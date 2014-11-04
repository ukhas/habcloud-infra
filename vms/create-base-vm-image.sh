#!/bin/bash
#
# Create base Debian install at /tmp/debian-7-amd64-vm.img. This script must be
# run from the directory which contains it. (Sorry.)
#
# Usage:
#     create-base-vm-image.sh [<name> [<imgpath>]]
#
# <name> is the name of the guest in libvirt. If omitted, "debian-7" is used.
# <imgpath> is the path to the created image. If omitted,
# "/tmp/<name>-amd64-vm.img" is used.

# Parse command line
vm_name=debian-7
if [ $# -gt 0 ]; then
	vm_name=$1; shift
fi

img_path=/tmp/${vm_name}-amd64-vm.img
if [ $# -gt 0 ]; then
	img_path=$1; shift
fi

if [ $# -gt 0 ]; then
	cat >&2 <<EOL
Usage:
    create-base-vm-image.sh [<name> [<imgpath>]]
EOL
	exit 1
fi

# Now command line is parsed, switch on logging and fail on error
set -xe

virt-install --virt-type kvm --name "${vm_name}" --ram 1024				\
	--location=http://ftp.debian.org/debian/dists/wheezy/main/installer-amd64/	\
	--disk "path=${img_path},size=5" --network network=default			\
	--noautoconsole --os-type=linux --initrd-inject=preseed.cfg			\
	--os-variant=debianwheezy --extra-args="priority=critical interface=auto	\
		debian-installer/language=en debian-installer/country=GB		\
		debian-installer/locale=en_GB keymap=gb console=ttyS0,115200n8"
