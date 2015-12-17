FROM python:3.5

MAINTAINER Arnold Bechtoldt <mail@arnoldbechtoldt.com>

RUN apt-get update -qq
RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -yV -o DPkg::Options::=--force-confold libffi6 gnupg2
RUN pip install tabellarius
RUN apt-get clean; rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
