FROM quay.io/centos/centos:stream8

RUN echo "tsflags=nodocs" >> /etc/yum.conf && \
    yum -y install git glibc-langpack-en epel-release python3-pip && \
    yum clean all

ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8
ENV LC_ALL en_US.UTF-8
ENV PYTHONUNBUFFERED=0

ARG VERSION=master
ARG REPO=theforeman/obal.git

RUN dnf config-manager --add-repo https://downloads.kitenet.net/git-annex/linux/current/rpms/git-annex.repo

RUN pip3 install --upgrade pip
RUN pip3 install git+https://github.com/${REPO}@${VERSION}
RUN obal setup

RUN mkdir -p /opt/packaging
WORKDIR /opt/packaging

ENTRYPOINT ["/usr/bin/obal"]
CMD ["--help"]
