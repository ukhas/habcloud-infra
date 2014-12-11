# Debian install

Debian installer booted 
  - with bnx2 firmware embedded
  - with command line `append install vga=normal initrd=initrd.gz fb=false console=tty0 console=ttyS1,9600n8`

iLO commands:
  - `ilo-> vm cdrom insert http://www.danielrichman.co.uk/files/bnx2-deb7.iso`
    (sha256sum 77d8ad8c5bbf09a71c1d855b57460953ee5186b7d027403d3ea8735ac2bb3f2e)
  - `ilo-> vm cdrom set boot_once`
  - `ilo-> power on`

Disk config: Raid 10, stripe across 3 mirror pairs + 2 hot spares (set before boot)
TODO: check config (IIRC problems), set up `hpaucli`, set up monitoring

Debian installer
  - Static configure networking.
  - Single LVM partition on raid disks.
  - Volume group name: phorcys
  - 8192M partition “host-root” ext4 /

Post install tasks
  - configure passwordless sudo
  - `apt-get install rsync vim git iperf`
  - `apt-get install qemu-kvm libvirt-bin qemu-system bridge-utils ifenslave`
  - `apt-get purge dnsmasq-base`
  - `apt-get install virtinst --no-install-recommends`
  - add yourself to group libvirt
  - install `/etc/profile.d/libvirt-default-uri.sh`
  - install `/etc/network/interfaces` (set the correct IP!)
    you may need to use `mii-tool` to inspect ports
  - install `/etc/iptables.rules`
  - install `/etc/network/if-pre-up.d/iptables`
  - install `/etc/network/if-pre-up.d/ebtables`
  - `sudo virsh net-undefine default`
  - reboot and check all networking comes up.
  - `sudo virsh net-create libvirt-br0.xml`
  - `sudo virsh net-create libvirt-br1.xml`
  - `sudo virsh pool-create libvirt-lvm-pool-$HOSTNAME.xml`

Virsh notes:

To copy img into storage volume:

  - `virsh vol-create-as $HOSTNAME new-name 5G` (the pools are named after the lvm vgroups)
  - `virsh vol-upload --pool $HOSTNAME new-name /path/to.img`

