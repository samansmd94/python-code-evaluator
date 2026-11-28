FROM public.ecr.aws/docker/library/python:3.14.7-slim-bookworm@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56

RUN groupadd --gid 10001 evaluator \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin evaluator

WORKDIR /opt/evaluator
COPY --chown=root:root worker.py /opt/evaluator/worker.py
RUN chmod 0555 /opt/evaluator/worker.py

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 10001:10001
ENTRYPOINT ["python", "-I", "/opt/evaluator/worker.py"]
