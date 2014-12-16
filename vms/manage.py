#!/usr/bin/env python

from __future__ import print_function, unicode_literals, division

import sys
import os
import os.path
import signal
import copy
import argparse
import tempfile
import subprocess
from platform import node as hostname
from contextlib import contextmanager

import yaml
import jinja2
import libvirt

LIBVIRT_URI = "qemu:///system"
AVAILABLE = {
    'public': set(range(115, 124 + 1)),
    'private': set(range(2, 254 + 1))
}
HOST_NETWORKS = {
    'ceto': {
        'public':  ('br0', '52:54:01:00:00:{0:02X}', '164.39.7.{0:d}'),
        'pubpriv': ('br1', '52:54:01:01:01:{0:02X}', '10.0.1.{0:d}'),
        'private': ('br1', '52:54:01:01:03:{0:02X}', '10.0.3.{0:d}')
    },
    'phorcys': {
        'public':  ('br0', '52:54:02:00:00:{0:02X}', '164.39.7.{0:d}'),
        'pubpriv': ('br1', '52:54:02:01:02:{0:02X}', '10.0.2.{0:d}'),
        'private': ('br1', '52:54:02:01:04:{0:02X}', '10.0.2.{0:d}')
    }
}
HOST_CPUS = {"ceto": 4, "phorcys": 8}


jinja_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_loader = jinja2.FileSystemLoader(jinja_dir)
jinja_env = jinja2.Environment(loader=jinja_loader, undefined=jinja2.StrictUndefined)


def available_addr_ids(db):
    networks = copy.deepcopy(AVAILABLE)

    for host in db.values():
        network, addr_id = host["ip"]
        networks[network].remove(addr_id)

    return networks

def allocate(db, host, vm_name, ram, vcpus, disk, network):
    if vm_name in db:
        raise ValueError("{0} already in database".format(vm_name))
    if vcpus > HOST_CPUS[host]:
        raise ValueError("{0} only has {1} cores".format(host, HOST_CPUS[host]))


    networks = available_addr_ids(db)
    available = networks[network]

    try:
        addr_id = available.pop()
    except KeyError:
        raise ValueError("Network {0} exhausted".format(network))

    db[vm_name] = {
        "host": host,
        "ram": ram,
        "vcpus": vcpus,
        "disk": disk,
        "ip": (network, addr_id)
    }

def expand_config(vm_name, vm):
    network, addr_id = vm["ip"]
    host_network_config = HOST_NETWORKS[vm["host"]]

    def interface(dev, key):
        network_dev, mac_template, ip_template = host_network_config[key]
        return {
            "dev": dev,
            "network": network_dev,
            "mac": mac_template.format(addr_id),
            "ip": ip_template.format(addr_id)
        }

    if network == "public":
        interfaces = [interface(0, "pubpriv"), interface(1, "public")]
    elif network == "private":
        interfaces = [interface(0, "private")]
    else:
        assert False

    return {
        "host": vm["host"],
        "vm_name": vm_name,
        "ram": vm["ram"],
        "vcpus": vm["vcpus"],
        "disk": vm["disk"],
        "interfaces": interfaces
    }


def domain_xml(vm):
    template = jinja_env.get_template('domain.xml')
    return template.render(**vm)

def dnsmasq_file(db, host, template):
    assert template in {'hosts', 'dhcp'}
    vms = [expand_config(name, cfg) for name, cfg in db.items()]
    template = jinja_env.get_template('dnsmasq-' + template)
    return template.render(host=host, vms=vms)


def check_call(command):
    print(*command, file=sys.stderr)
    subprocess.check_call(command)

def need_root():
    if os.getuid() != 0:
        raise OSError("Need root")


def create(db, conn, vm_name):
    need_root()

    vm = expand_config(vm_name, db[vm_name])
    host = hostname()

    if host != vm["host"]:
        raise Exception("Must be run on {0}".format(vm["host"]))
    if vm_name in conn.listDefinedDomains():
        raise KeyError(vm_name + " already exists")

    assert host in {"ceto", "phorcys"}

    print("Defining", vm_name, file=sys.stderr)
    domain = conn.defineXML(domain_xml(vm))

    lvcreate = [
        "lvcreate", "--quiet",
        vm["host"],
        "--name", "vm-{0}".format(vm_name),
        "--size", "{amt}{unit}".format(**vm["disk"])
    ]
    check_call(lvcreate)

    virt_resize = [
        "virt-resize", "-q",
        "--expand", "/dev/sda1",
        "/dev/{0}/vm-base".format(host),
        "/dev/{0}/vm-{1}".format(host, vm_name)
    ]
    check_call(virt_resize)

    print("Starting", vm_name, file=sys.stderr)
    domain.create()

def sync_dnsmasq(db):
    need_root()
    host = hostname()

    if host not in {"ceto", "phorcys"}:
        raise ValueError("Need to be run on ceto or phorcys", host)

    for fn in ("dhcp", "hosts"):
        print("Writing dnsmasq/{0}...".format(fn), file=sys.stderr)
        with open("/etc/dnsmasq/{0}".format(fn), "w") as f:
            f.write(dnsmasq_file(db, host, fn))

    with open("/run/dnsmasq/dnsmasq.pid") as f:
        pid = int(f.read())

    print("HUP dnsmasq ({0})".format(pid), file=sys.stderr)
    os.kill(pid, signal.SIGHUP)


def read_db(filename):
    with open(filename, 'r') as f:
        db = yaml.safe_load(f)
        if db == None:
            return {}
        else:
            return db

@contextmanager
def change_db(filename):
    with open(filename, 'a+') as f:
        db = yaml.safe_load(f)
        if db == None:
            db = {}
        yield db
        f.truncate(0)
        yaml.safe_dump(db, f)


def cmd_allocate(args):
    with change_db(args.db) as db:
        allocate(db=db, host=args.host, vm_name=args.vm_name, ram=args.ram,
                        vcpus=args.vcpus, disk=args.disk, network=args.network)
        cfg = expand_config(args.vm_name, db[args.vm_name])
    yaml.safe_dump(cfg, sys.stdout)

def cmd_list(args):
    table = []
    db = read_db(args.db)

    for key in sorted(db.keys()):
        vm = config_for(db, key)
        row = (vm["vm_name"], vm["host"])
        row += tuple(intf["ip"] for intf in vm["interfaces"])
        table.append(row)

    for row in table:
        print(*row, sep='\t')

def cmd_show(args):
    db = read_db(args.db)
    vm = expand_config(args.vm_name, db[args.vm_name])
    yaml.safe_dump(vm, sys.stdout)

def cmd_xml(args):
    db = read_db(args.db)
    vm = expand_config(args.vm_name, db[args.vm_name])
    print(domain_xml(vm))

def cmd_dnsmasq_print(args):
    db = read_db(args.db)
    print(dnsmasq_file(db, args.host, args.template), end='')

def cmd_create(args):
    db = read_db(args.db)
    conn = libvirt.open(LIBVIRT_URI)
    create(db, conn, args.vm_name)

def cmd_sync_dnsmasq(args):
    db = read_db(args.db)
    sync_dnsmasq(db)


def main():
    def parse_amount_units(s, allowed_units):
        for u in allowed_units:
            if s.endswith(u):
                amt = int(s[:-len(u)])
                if amt <= 0:
                    raise ValueError(s)
                return {"unit": u, "amt": amt}
        else:
            raise ValueError(s)

    def ram(s): return parse_amount_units(s, {"GiB", "MiB"})
    def vcpus(s):
        n = int(s)
        if n < 0:
            raise ValueError(n)
    def disk(s): return parse_amount_units(s, {"G", "M"})


    parser = argparse.ArgumentParser()
    parser.add_argument("--db", help='VMs database', default="./vms.yaml")
    subparsers = parser.add_subparsers()

    allocate = subparsers.add_parser("allocate")
    allocate.set_defaults(func=cmd_allocate)
    allocate.add_argument("host", help='VM host', choices=HOST_NETWORKS.keys())
    allocate.add_argument("vm_name", help='guest hostname')
    allocate.add_argument('--ram', type=ram, help='RAM, with units MiB or GiB',
                          default={"unit": "GiB", "amt": 1})
    allocate.add_argument('--vcpus', type=vcpus, default=1)
    allocate.add_argument('--disk', type=disk, default="2G")
    allocate.add_argument('--public-ip', action='store_const', dest='network',
                          default='private', const='public')

    list = subparsers.add_parser("list")
    list.set_defaults(func=cmd_list)

    show = subparsers.add_parser("show")
    show.set_defaults(func=cmd_show)
    show.add_argument("vm_name", help='guest hostname')

    xml = subparsers.add_parser("xml", help='libvirt domain xml')
    xml.set_defaults(func=cmd_xml)
    xml.add_argument("vm_name", help='guest hostname')

    dnsmasq_dhcp = subparsers.add_parser("dnsmasq-dhcp", help='dnsmasq dhcp-hosts file')
    dnsmasq_dhcp.set_defaults(func=cmd_dnsmasq_print, template='dhcp')
    dnsmasq_dhcp.add_argument("host", help='VM host', choices=HOST_NETWORKS.keys())

    dnsmasq_hosts = subparsers.add_parser("dnsmasq-hosts", help='dnsmasq hosts file')
    dnsmasq_hosts.set_defaults(func=cmd_dnsmasq_print, template='hosts')
    dnsmasq_hosts.add_argument("host", help='VM host', choices=HOST_NETWORKS.keys())

    create = subparsers.add_parser("create", help='create an allocate VM on this box')
    create.set_defaults(func=cmd_create)
    create.add_argument("vm_name", help='guest hostname')

    sync_dnsmasq = subparsers.add_parser("sync-dnsmasq", help='sync and HUP dnsmasq on this box')
    sync_dnsmasq.set_defaults(func=cmd_sync_dnsmasq)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
