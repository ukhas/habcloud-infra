# HabCloud Monitoring Thoughts

There are a whole heap of options for monitoring. This document evaluates some 
of them and how they might fit into HabCloud, plus what potential alternatives 
we might consider.

## Our Priorities

 * Alerts when 'things' 'break'
    * Application errors
    * Processes or hosts go down
    * Abnormal load / disk usage / RAM usage
 * Keep log files somewhere easy to store and analyse and rotate
 * Record interesting statistics
    * Hits on websites
    * Predictions run
    * Response time for predictions/habitat/etc
    * Cache hits/misses
 * Pretty dashboards to display system status and drill down into metrics
 * Don't spend too much CPU or RAM on monitoring

## Vague Outline

We run applications and other services on hosts.

Applications generate errors, log files and interesting statistics (time to run 
function, number of runs, etc) and might be running or not.

Services (varnish, nginx, postgresql, etc) generate log files from which 
metrics like website hits might be derived, and metrics like memory usage or 
active connections or threads, and might be running or not.

Hosts have properties (disk usage, RAM usage, CPU, load, etc) and might be 
running or not.

We want to be alerted to application errors and downtime, some service errors 
and downtime, abnormal host properties and downtime. We want to view pretty 
charts of the interesting statistics. We want to easily view log files and 
derive statistics from them too.

Probably we want to do this by having some service or two run on every host to 
collect host properties and application statistics (though these could go 
direct to the top level collection), and then run one VM that runs the rest of 
the monitoring and alerting stack.

Finally some external monitoring system (Pingdom, Anthony's nagios, etc) can 
alert us if the entire thing goes sad.

An additional thing that might be interesting to monitor is application 
deployments or other configuration changes based on Salt. For instance, 
generate an event when Salt runs a deploy, and link it to the list of things 
that changed on that Salt push. So if RAM usage starts going up, or something 
starts generating a lot of errors, we can easily see it started happening after 
a specific Salt run that deployed a new version of our application. This could 
feasibly be integrated into Saltbot (which already provides a web view of what 
changed in each run).

## Software Not Being Considered

 * Nagios is a pain to set up and configure and update, and is slow and old.
 * Monit is kind of dumb and boring.
 * Graphite is a pain to set up and its storage options leave something to be 
   desired. InfluxDB should replace it well.

## Software Options

### [Sentry](http://sentry.readthedocs.org): Application Error Monitoring

Sentry is available as an open source system or a paid-for SaaS. Applications
report errors to Sentry, which does alerting with roll-up and history. We get 
to see if this sort of exception has happened before, when/where, get email 
alerts about exceptions, etc. It comes highly recommended and is standalone 
(with PostgreSQL and Redis and nginx as requirements).

We run one Sentry server and then every application to be monitored includes 
the relevant Sentry library and sends events to the server.

Written in Python with Python and other language clients. Install with pip.

### [Diamond](https://github.com/BrightcoveOS/Diamond): System Metrics Gathering

Diamond collects system metrics (CPU, disk, RAM, load, a variety of
[other metrics](https://github.com/BrightcoveOS/Diamond/wiki/Collectors)) and 
sends them to InfluxDB, Riemann, StatsD, Sentry etc.

We'd use it to collect basic stats on each host and store and alert based on 
those metrics. This (plus upstream alerting) can replace Monit. We currently 
use it on kraken/tiamat to send host metrics into Graphite and it's done that 
job well.

Runs one instance on every host in the cloud.

Written in Python, install with pip. Easy enough to put on every host.

### [CollectD](https://collectd.org/): System Metrics Gathering

Competes with Diamond. Has more plugins available for collecting from other 
services. Runs a statsd server which application-level metrics could be 
reported to before being sent up to Riemann/Influx/etc.

Runs one instance on every host in the cloud.

Written in C though. Is available in apt so easy to install per-host, but would 
need a (binary) Riemann plugin distributed to send to Riemann.

### StatsD: Metric aggregator

StatsD is a server (and also now a common protocol) for collecting events like 
website hits, execution times, etc from an application (we use this to count 
predictions and measure habitat parsing time right now). Clients send these 
events to a local (or global, but typically local) statsd server which rolls 
them up into one metric per minute (containing e.g. hits per minute, 
average+stddev+95%+99% of times) which gets sent on to 
(graphite/influxdb/riemann/other collection).

StatsD itself is probably not what we'd run (there is a Python alternative 
rather than the nodeJS "official" one), but many per-host things (Heka, 
CollectD) run a statsd server which might be useful. Alternatively we can 
update our applications to report directly to Riemann instead of going through 
statsd, and have Riemann (or InfluxDB above that) perform the aggregation.

Originally developed by Etsy.

### [Heka](http://hekad.readthedocs.org/): Metric Collection / Processing

Collects metrics. Probably we'd need something like Diamond or CollectD to 
report system metrics into Heka. Also runs a statsd server so application-level 
metrics can be reported easily. Does a good job of reading log files from 
applications and sending them to something like ElasticSearch, replacing 
Logstash. Performs some metric processing and alerting, replacing Riemann.

Does not store metrics, forwards to something like InfluxDB or Graphite or 
higher-level Heka instances.

Includes a reasonably pretty dashboard but we probably would not generally be 
using it.

Heka is a statically linked Go binary so it's easy to deploy to each host. 
Plugins can be written in Go or Lua.

Developed by Mozilla.

### [Sensu](http://sensuapp.org/): Metric Collection

Looks vaguely similar to Heka. Runs on each host I think. Can do 
processing/alerting too but mostly focussed on collection. Perhaps can collect 
system-level metrics itself.

### [Flapjack](http://flapjack.io): Metric Alerting

Configurable alerts based on metrics. Commonly used with Sensu I think. 
Probably less configurable than Riemann but does have a fancier website.

### [Skyline & Oculus](https://codeascraft.com/2013/06/11/introducing-kale/)

Etsy's clever thing. Skyline alerts you to abnormalities in your metric time 
series, _all automatically_, which is nice if you have 250k different metrics. 
Oculus finds correlated metrics, so if one fails you can find other similar 
ones that might be related. Both are fairly intensive CPU/RAM wise and probably 
more advanced than we need right now. Skyline is Python, Oculus is Ruby.

### [Riemann](http://riemann.io): Metric Collection / Processing

Collects, processes and alerts based on metrics. Something like Diamond reports 
host properties, while applications can report to Riemann directly or via a 
statsd server (but Riemann does not include a statsd server itself). Can handle 
text data (log entries, application errors) quite well too.

Advanced/powerful features when it comes to processing streams of events to 
generate rates or averages, alerting with rollup and on special conditions etc.

Does not store metrics, forwards to something like InfluxDB or Graphite or ES.

Has a basic dashboard (not built in but available as a Ruby gem) which is an 
interesting way to quickly see the current-state (no history) of metrics being 
collected.

Developed by aphyr, written in Clojure (configuration file is also Clojure 
code). Packages exist for Debian but no repository.

Riemann looks very nice for metric processing and alerting. Running on the JVM 
and being configured in Clojure are probably downsides. Probably mutually 
exclusive with Heka though.

### [Prometheus](http://prometheus.io/): Metric collection, processing, storage, display, alerting

A nice integrated solution to monitoring. Neat high dimensional model for data 
allows good querying. Does its own storage. Built in dashboard and 
visualisation. Built in alerting with flexible query language. Written in Go so 
statically linked binaries. Accepts system metrics from CollectD. Written by 
Soundcloud.

Downsides: pull-based model means all _applications_ run a Prometheus _web 
server_ which the master service polls for data. No client library currently 
available for Python (Go, Ruby, Java atm) but it's in the works.

### [InfluxDB](http://influxdb.com/): time series storage

Time series input, storage, output. Can perform basic analysis too. Written in 
Go. A popular replacement for Graphite and in active development. Most modern 
tools can write to it, e.g. Heka and Riemann. Typically used with Grafana for 
dashboards/visualisation.

### [Grafana](http://grafana.org): pretty metrics dashboards

Grafana is a replacement for graphite-web that provides pretty dashboards. 
Integrates with Graphite or InfluxDB (or others). Stores configurations for 
dashboards in ElasticSearch (but perhaps elsewhere is possible too).

Currently it's just static HTML+JS so super easy to deploy. In the future v2 
will include a backend app doing auth and storage and other things.

### [Logstash](http://logstash.net): logfile forwarding

Logstash reads log files and sends them on to a log file index. We could 
probably use Heka instead for this. Logstash itself is a bulky Java thing but 
logstash-forwarder is a small binary that can run on hosts and forward log 
entries to a master Logstash instance.

Logstash can output metrics from logs (like hit counts, rates, etc?) to statsd 
or influxDB or riemann.

Logstash is written in JRuby so requires the JVM.

Not clear right now if we'd need Logstash at all if we ran Heka. Looks like no.

### [syslog-ng](https://github.com/balabit/syslog-ng): log collection

Instead of having apps write to log files, we could send to syslog-ng. Can 
output to logstash and riemann. Can replace local syslog or local host syslogs 
can be configured to just forward to a central syslog-ng.

### [ElasticSearch](http://elasticsearch.org): log storage (and other things)

Stores log files. Primarily useful in combination with Heka/Logstash to get the 
logs into it, and Kibana to view the logs out of it. Also used by Grafana to 
store dashboards.

### [Kibana](http://www.elasticsearch.org/overview/kibana/): Log dashboard

View log entries and charts/metrics derived from them. Apparently very nice.

### [Piwik](http://piwik.org/): Website analytics

Somewhat separate from everything else, Piwik analyses log files (and perhaps 
has a little javascript widget too) that does web analytics. A sort of 
self-hosted Google Analytics service.

## Proposal / Options

We should set up Sentry for application errors. This meets our "alert on 
application errors" requirement.

We should get log files into ElasticSearch+Kibana somehow (logstash or heka 
seem likely candidates). This meets our "store and view all log files" 
requirement.

We should run InfluxDB+Grafana for storing and displaying interesting metrics. 
This meets our "visualise interesting stats in a pretty way" requirement.

We should run Piwik on our web logs, possibly fed from the 
ElasticSearch/LogStash setup (or perhaps fed directly, not sure).

Running Diamond on each host probably makes the most sense, collecting system 
metrics and sending them to Riemann or Heka or something else. CollectD is a 
reasonable alternative and would give us a statsd server, though. These fulfill 
the first part of being able to "alert on abnormal system state".

### Logging Choices

No matter what, we'll probably end up with logs being stored in ElasticSearch 
and visualised with Kibana. How they get there is the choice.

 * logstash-forwarder on each host, to a central logstash server
 * heka can read log files and write to elasticsearch directly (apparently more 
   performant too)
 * syslog on each host sends logs to syslog-ng which sends to logstash. can't 
   deal with log files, only syslog entries, though. might be OK.
 * syslog-ng (or perhaps others) can send logs to riemann which can write to 
   elasticsearch. This seems an unusual approach though. Riemann seems more 
   designed to input the events that would otherwise generate a line in a log 
   file.

We probably then want to aggressively remove log files from disk on the hosts. 

### Metrics Choices

 * We could run Riemann. Apps send metrics to Riemann directly, it does 
   analysis and alerting and sends to InfluxDB for long term storage. We just 
   run one Riemann instance, so JVM requirement isn't too bad. We get advanced 
   monitoring/alerting capability. We don't get statsd anywhere.

 * We could run Heka. We'd run it on every host, plus probably one central 
   instance. On each host it runs statsd for application metrics, some 
   applications could report to it directly, and it can do basic alerting. It 
   then outputs to InfluxDB. We have to run it on every host (but that's not 
   too onerous). We get less flexible alerting. It can read log files for us 
   and send them to ElasticSearch/LogStash. It's not clear if Heka and Riemann 
   can usefully coexist, though.

Alerting on application or service downtime is doable in Riemann and probably 
in Heka based on the absence of heartbeat or other regular metrics.

## Appendix: Interesting Links

Scripts to install a lot of tools on Debian/Ubuntu:
https://github.com/ianunruh/monitoring

List of a lot of tools:
https://github.com/benhaines/open-source-management-systems

Someone else had similar problems, started writing their own collection and 
management and etc:

 1. https://gist.github.com/ceejbot/032e545a9f2aebee7cc6
 2. https://gist.github.com/ceejbot/eb5cb1c7d4f7330175e6
 3. https://github.com/ceejbot/numbat-collector/blob/master/README.md
 4. https://github.com/ceejbot/numbat-analyzer/blob/master/README.md

Python+Riemann:

 * http://spootnik.org/entries/2013/05/21_using-riemann-to-monitor-python-apps.html
 * https://pypi.python.org/pypi/riemann_wrapper/
 * https://github.com/banjiewen/bernhard
 * https://github.com/borntyping/python-riemann-client
