#!/usr/bin/env python

from __future__ import print_function, unicode_literals, division
from contextlib import contextmanager
import sys
import os.path
import copy
import argparse

import yaml
import jinja2


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

def allocate(db, host, vm_name, ram, vcpus, network):
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
        "interfaces": interfaces
    }


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
        allocate(db, args.host, args.vm_name, args.ram, args.vcpus, args.network)
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
    template = jinja_env.get_template('domain.xml')
    print(template.render(**vm), end='')

def cmd_dnsmasq(args):
    db = read_db(args.db)
    vms = [expand_config(name, cfg) for name, cfg in db.items()]
    template = jinja_env.get_template('dnsmasq-' + args.template)
    print(template.render(host=args.host, vms=vms), end='')


def main():
    def ram(s):
        units = {"GiB", "MiB"}
        for u in units:
            if s.endswith(u):
                amt = int(s[:-len(u)])
                if amt <= 0:
                    raise ValueError(s)
                return {"unit": u, "amt": amt}
        else:
            raise ValueError(s)

    def vcpus(s):
        n = int(s)
        if n < 0:
            raise ValueError(n)

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
    dnsmasq_dhcp.set_defaults(func=cmd_dnsmasq, template='dhcp')
    dnsmasq_dhcp.add_argument("host", help='VM host', choices=HOST_NETWORKS.keys())

    dnsmasq_hosts = subparsers.add_parser("dnsmasq-hosts", help='dnsmasq hosts file')
    dnsmasq_hosts.set_defaults(func=cmd_dnsmasq, template='hosts')
    dnsmasq_hosts.add_argument("host", help='VM host', choices=HOST_NETWORKS.keys())

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
