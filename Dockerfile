FROM python:2.7

MAINTAINER Dmitry Korobitsin <korobicin@gmail.com>

RUN apt-get update && apt-get install smitools

COPY . /tmp/compiler/

RUN set -x \
    && pip install -r /tmp/compiler/requirements.txt
    && pip install /tmp/compiler \
    && rm -rf /tmp/compiler

CMD ["mib_compiler"]
