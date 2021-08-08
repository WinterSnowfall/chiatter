#!/bin/bash
docker run -d --name prometheus --net=host -v $PWD/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus
docker run -d --name grafana --net=host -v $PWD/datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml grafana/grafana:main-ubuntu

