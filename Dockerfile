FROM opensciencegrid/software-base:3.6-el8-release

# Install dependencies (application, Apache)
RUN \
    yum update -y \
    && yum install -y \
      gcc \
      python3-devel \
      python3-pip \
    && yum install -y \
      httpd \
      httpd-devel \
      singularity \
    && yum clean all && rm -rf /var/cache/yum/* \
    && mkdir /app

WORKDIR /app

# Install application dependencies
COPY pyproject.toml setup.cfg examples/condor_lock.patch /app/

RUN pip3 install --upgrade pip setuptools && useradd -m soteria && mkdir -m 0700 /home/soteria/.singularity && \
    chown soteria: /home/soteria/.singularity && \
    touch /etc/sysconfig/httpd && mkdir /wsgi && cd / && (patch -p0 < /app/condor_lock.patch || : ) && \
    curl -L https://dl.k8s.io/release/v1.24.0/bin/linux/amd64/kubectl > /app/kubectl && \
    chmod +x /app/kubectl

COPY src /app/src
RUN pip3 install --no-cache-dir /app

COPY examples/apache.conf /etc/httpd/conf.d/soteria-sync-manager.conf
COPY examples/supervisor-apache.conf /etc/supervisord.d/40-apache.conf
COPY examples/soteria_sync.wsgi /wsgi

EXPOSE 8080/tcp
