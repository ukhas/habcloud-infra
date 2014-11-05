#!/bin/bash
#
# Create base Debian install at /tmp/debian-7-amd64-vm.img. This script must be
# run from the directory which contains it. (Sorry.)
#
# Usage:
#     create-base-vm-image.sh [<imgpath> [<name>]]
#
# <name> is the name of the guest in libvirt. If omitted, "debian" is used.
# <imgpath> is the path to the created image. If omitted,
# "/tmp/debian-amd64-vm.img" is used.

# Parse command line
img_path=/tmp/debian-amd64-vm.img
if [ $# -gt 0 ]; then
	img_path=$1; shift
fi

vm_name=debian
if [ $# -gt 0 ]; then
	vm_name=$1; shift
fi

if [ $# -gt 0 ]; then
	cat >&2 <<EOL
Usage:
     create-base-vm-image.sh [<imgpath> [<name>]]
EOL
	exit 1
fi

# Now command line is parsed, switch on logging and fail on error
set -xe

# Create the VM image
virt-install --virt-type kvm --name "${vm_name}" --ram 1024 --wait 20 --noreboot	\
	--location=http://ftp.debian.org/debian/dists/wheezy/main/installer-amd64/	\
	--disk "path=${img_path},size=5" --network network=br0			\
	--graphics none --os-type=linux --initrd-inject=preseed.cfg			\
	--os-variant=debianwheezy --extra-args="priority=critical interface=auto	\
		debian-installer/language=en debian-installer/country=GB		\
		debian-installer/locale=en_GB keymap=gb console=ttyS0,115200n8"

# Destroy and undefine the VM now we've started creating the image
virsh destroy "${vm_name}" || echo "${vm_name} not destroyed"
virsh undefine "${vm_name}" || echo "${vm_name} not undefined"
