# VMs database

Since we have free choice of MACs, and won't be deploying very many VMs,
we can have an incredibly simple allocation strategy. See the `host-setup`
folder for details of IP address allocation.

In practice, there are two "namespaces": `private` and `public`. Each has a
set of integers that are available; for `public` this is restricted by
the IPv4 addresses we have available, and for `private` it is 2-254.

The database simply stores VM hostname, VM host (i.e., ceto or phorcys), RAM,
and a `(network, id)` pair. The IP addresses and MACs may all be synthesised
from this. The easiest explanation of how is to look at the format strings
at the top of `manage.py`.

The intention is to have the database checked into git.
