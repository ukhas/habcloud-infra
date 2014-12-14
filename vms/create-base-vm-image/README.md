# HabHub Cloud VM images

This directory contains configuration and scripts for generating initial HabHab
VM images. The [preeseed.cfg](preeseed.cfg) file specifies a base setup for the
Debian images and [create-base-vm-image.sh](create-base-vm-images.sh) uses
[virt-install](http://docs.openstack.org/image-guide/content/virt-install.html)
to form an initial image.

The image is created at ``/dev/VG/vm-base``. Installation is entirely
automated, but it will attach to the virtual serial console to view progress.
You can also connect to the console tomonitor progress using ``virsh``:

```console
$ virsh console vm-base
```

## Required packages

* ``virtinst`` for ``virt-install``
* ``qemu-system`` for libvirt to work at all

## Optional packages

* ``libguestfs-tools`` for the useful ``guestfish`` tool
* ``virt-manager`` for GUI configuration of domains
