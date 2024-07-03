# SPDX-License-Identifier: MIT
# Define the tags for OBS and build script builds:
#!BuildTag: %%TAGPREFIX%%/demo:latest
#!BuildTag: %%TAGPREFIX%%/demo:%%PKG_VERSION%%
#!BuildTag: %%TAGPREFIX%%/demo:%%PKG_VERSION%%-%RELEASE%

#FROM opensuse/tumbleweed
ARG OS=opensuse/tumbleweed
FROM ${OS}

# Mandatory labels for the build service:
#   https://en.opensuse.org/Building_derived_containers
# labelprefix=%%LABELPREFIX%%
LABEL Description="Graph requires Container"
LABEL maintainer="Antoine Ginies <aginies@suse.com>"

LABEL org.opencontainers.image.title="graph container"
LABEL org.opencontainers.image.description="Container for graph requires"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.version="%%PKG_VERSION%%.%RELEASE%"
LABEL org.opencontainers.image.url="https://build.opensuse.org/package/show/home:aginies:branches:openSUSE:Templates:Images:Tumbleweed/graph-container"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL org.opensuse.reference="%%REGISTRY%%/%%TAGPREFIX%%/graph-container:%%PKG_VERSION%%.%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="test"
LABEL com.suse.eula="beta"
LABEL com.suse.image-type="application"
LABEL com.suse.release-stage="prototype"
# endlabelprefix

RUN mkdir /container
RUN mkdir /tmp/graph
COPY graph_requires.py /container
RUN chmod +x /container/graph_requires.py

RUN zypper install --no-recommends -y \
	graphviz \
	graphviz-gd \
	python3-base \
  && zypper clean --all

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT [ "/entrypoint.sh" ]
