FROM quay.io/centos/centos:stream8

RUN echo "tsflags=nodocs" >> /etc/yum.conf && \
    dnf -y install git glibc-langpack-en epel-release python3-pip dnf-utils && \
    dnf clean all

ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    PYTHONUNBUFFERED=0

ARG VERSION=master
ARG REPO=theforeman/obal.git

RUN dnf config-manager --add-repo https://downloads.kitenet.net/git-annex/linux/current/rpms/git-annex.repo && \
    pip3 install --upgrade pip && \
    pip3 install git+https://github.com/${REPO}@${VERSION} && \
    obal setup

RUN mkdir -p /opt/packaging
WORKDIR /opt/packaging

ENTRYPOINT ["/usr/bin/obal"]
CMD ["--help"]
