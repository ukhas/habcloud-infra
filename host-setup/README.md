# Debian install

Debian installer booted 
  - with bnx2 firmware embedded
  - with command line `append install vga=normal initrd=initrd.gz fb=false console=tty0 console=ttyS1,9600n8`

iLO commands:
  - ilo-> vm cdrom insert http://www.danielrichman.co.uk/files/bnx2-deb7.iso 77d8ad8c5bbf09a71c1d855b57460953ee5186b7d027403d3ea8735ac2bb3f2e
  - ilo-> vm cdrom set boot_once
  - ilo-> power on

Disk config: Raid 10, stripe across 3 mirror pairs + 2 hot spares (set before boot)
TODO: check config (IIRC problems), set up hpaucli, set up monitoring

Debian installer
  - Static configure networking.
  - Single LVM partition on raid disks.
  - Volume group name: phorcys
  - 8192M partition “host-root” ext4 /

Post install tasks
  - configure passwordless sudo
  - add yourself to group libvirt
  - put `export LIBVIRT_DEFAULT_URI="qemu:///system"` in your bashrc
  - apt-get install rsync vim git iperf
  - apt-get install qemu-kvm libvirt-bin qemu-system bridge-utils
  - apt-get purge dnsmasq-base
  - apt-get install virtinst --no-install-recommends
  - sudo update-rc.d procps defaults
  - install /etc/sysctl.d/bridge-notables.conf
  - install /etc/network/interfaces (set static config!)
    you may need to use `apt-get install ethtool` to inspect ports
  - sudo virsh net-create libvirt-br0.xml
  - sudo virsh pool-create libvirt-lvm-pool-`hostname`.xml

Virsh notes:

To copy img into storage volume:

  - export POOL=`hostname` # The pools are named after the lvm vgroups
  - virsh vol-create-as $POOL new-name 5G
  - virsh vol-upload --pool $POOL new-name /path/to.img

