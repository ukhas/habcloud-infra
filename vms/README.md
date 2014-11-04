# HabHub Cloud VM images

This directory contains configuration and scripts for generating initial HabHab
VM images. The [preeseed.cfg](preeseed.cfg) file specifies a base setup for the
Debian images and [create-base-vm-image.sh](create-base-vm-images.sh) uses
[virt-install](http://docs.openstack.org/image-guide/content/virt-install.html)
to form an initial image.

The image is created at ``/tmp/debian-7-amd64-vm.img``. Installation proceeds
by attaching to the virtual serial console. You can connect to the console to
monitor progress using ``virsh``:

```console
$ virsh console debian-7
```
