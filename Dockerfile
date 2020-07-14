FROM centos:7

RUN echo "tsflags=nodocs" >> /etc/yum.conf && \
    yum -y install epel-release git && \
    yum -y install python2-pip && \
    yum clean all

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV PYTHONUNBUFFERED=0

ARG VERSION=VERSION
ARG REPO=theforeman/obal.git

RUN pip install git+https://github.com/${REPO}@${VERSION}
RUN obal setup

RUN mkdir -p /opt/packaging
WORKDIR /opt/packaging

ENTRYPOINT ["/usr/bin/obal"]
CMD ["--help"]
