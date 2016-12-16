# Prometheus PDNS exporter

```
usage: prometheus_pdns_exporter.py [-h] [--url URL] [--api_key API_KEY]
                                   [--api_key_file API_KEY_FILE]
                                   [--listen_host LISTEN_HOST]
                                   [--listen_port LISTEN_PORT]

Fetch PowerDNS metrics and export them for Prometheus

optional arguments:
  -h, --help            show this help message and exit
  --url URL, -u URL     URL to connect to (default: http://localhost:8082/api/
                        v1/servers/localhost/statistics
  --api_key API_KEY, -k API_KEY
                        PowerDNS API key
  --api_key_file API_KEY_FILE, -f API_KEY_FILE
                        File to read PowerDNS API key from
  --listen_host LISTEN_HOST, -l LISTEN_HOST
                        Host to listen on
  --listen_port LISTEN_PORT, -p LISTEN_PORT
                        Port to listen on
```

Scrapes the stats of a PowerDNS server (as exposed on its REST API) and
re-exports them as Prometheus-compatible metrics.

Dependencies: Python 3.x and https://github.com/prometheus/client_python

## Limitations

I only wrote this for the PowerDNS recursor. It *should* work with the
authorative server, too.

The re-export itself is relatively dumb: I tried to make the non-counter metrics
marked as gauges, but I may have gotten that wrong.

Patches and pull requests are welcome.

## Why not use the existing PDNS exporter?

There is a PDNS exporter written in Go:

https://github.com/janeczku/powerdns_exporter

However, it has not seen a commit since January and still demands (rightly or
not) that Go 1.5 is installed. I would have liked to get it to compile on my
systems, but after a weekend of trying gave up, then wrote this in an evening.
