#!/bin/bash

docker pull prom/prometheus
docker pull grafana/grafana

docker run -d --name prometheus --net=host -v prometheus:/prometheus -v $PWD/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus --storage.tsdb.retention.time=1y --config.file=/etc/prometheus/prometheus.yml --storage.tsdb.path=/prometheus --web.console.libraries=/usr/share/prometheus/console_libraries --web.console.templates=/usr/share/prometheus/consoles
docker run -d --name grafana --net=host -v $PWD/datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml grafana/grafana

