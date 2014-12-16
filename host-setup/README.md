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
  - `apt-get install python-jinja2 python-yaml`
  - `apt-get install qemu-kvm libvirt-bin qemu-system bridge-utils ifenslave dnsmasq python-libvirt`
  - `apt-get install virtinst libguestfs-tools --no-install-recommends`
    you Do want to setup a supermin applaince.
  - add yourself to group libvirt
  - install all files in `etc`
  - reconfigure `/etc/network/interfaces` and `/etc/dnsmasq.conf` with the correct IPs and IP ranges
    you may need to use `mii-tool` to inspect ports
  - `sudo virsh net-undefine default`
  - reboot and check all networking comes up.
  - `sudo virsh net-create libvirt/br0.xml`
  - `sudo virsh net-create libvirt/br1.xml`
  - `sudo virsh pool-create libvirt/lvm-pool-$HOSTNAME.xml`

# IP Address allcation

## Public IPv4

  - ceto: `164.39.7.113`
  - phorcys: `164.39.7.114`
  - guests: `164.39.7.115--124`
  - no specific alocation convention

## Private IPv4

Each VM host has three ranges:

  - private addresses for VMs that also have public addresses
  - private addresses for VMs that don't have public addresses
  - temporary private addresses

The first two are statically assigned; the latter is a DHCP range. It's used by the debian installer, random recovery VMs, etc.

These are:

|         | private for dual-address  | private for private-only  | temporary    |
|---------|---------------------------|---------------------------|--------------|
| ceto    | 10.0.1.2-254              | 10.0.3.2-254              | 10.0.5.2-254 | 
| phorcys | 10.0.2.2-254              | 10.0.4.2-254              | 10.0.6.2-254 |

The private-only addresses are assigned sequentially.
The dual addresses are assigned by taking the last octet of the public address, e.g., you might have a VM on ceto with addresses `164.39.7.116` and `10.0.1.116` and one on phorcys with `164.39.7.115` and `10.0.2.115`.
Note that this applies to the hosts too, so (for example) the default router for VMs with private addresses only on ceto is `10.0.1.113`.
