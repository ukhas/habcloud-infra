# Setup

You'll need 
  - [the simple-kvm host-di-preseed](https://github.com/danielrichman/simple-kvm/tree/master/host-di-preseed)
  - [with bnx2 firmware embedded](https://github.com/danielrichman/preseed)
  - and probably a command line something like `append install vga=normal initrd=initrd.gz fb=false console=tty0 console=ttyS1,9600n8`

iLO commands, something like:
  - `ilo-> vm cdrom insert http://www.danielrichman.co.uk/files/bnx2-deb7.iso`
  - `ilo-> vm cdrom set boot_once`
  - `ilo-> power on`

Installer notes
  - disk config: Raid 10, stripe across 3 mirror pairs + 2 hot spares (needs to be done in hw raid controller config)
  - static networking
  - volume group vg0
  - root partition e.g. `physical4-root` 8G

Post install tasks
  - acquire and install [hpacucli](http://downloads.linux.hp.com/SDR/repo/mcp/pool/non-free/hpacucli_9.40.1-1._amd64.deb)
  - setup iptables using the files in `etc`

After [bootstrapping salt](../salt-config/bootstrapping.md)
  - Copy host-setup/etc/salt to /etc/salt
  - Add the salt Debian repo, install salt-minion, accept the key, and let it configure the rest of the master.

# IP Address allcation

## Public IPv4

  - ceto: `164.39.7.113`
  - phorcys: `164.39.7.114`
  - physical4: `164.39.7.123`
  - guests: `164.39.7.115--122`
  - no specific alocation convention

## Private IPv4

TODO: update for new physical4 style

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
