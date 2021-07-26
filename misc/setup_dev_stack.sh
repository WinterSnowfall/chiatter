#!/bin/bash
docker run -d --name prometheus --net=host -v $PWD/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus
docker run -d --name grafana --net=host grafana/grafana:main-ubuntu

