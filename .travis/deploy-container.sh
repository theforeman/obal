#!/bin/bash -x

docker build --build-arg VERSION=$1 -t quay.io/foreman/obal:latest .
docker tag quay.io/foreman/obal:latest quay.io/foreman/obal:$1
