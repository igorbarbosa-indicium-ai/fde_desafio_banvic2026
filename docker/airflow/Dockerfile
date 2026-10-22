FROM apache/airflow:2.10.5-python3.12

USER airflow
WORKDIR /opt/elt

RUN pip install --no-cache-dir "meltano==3.8.1" "SQLAlchemy<2.0"

COPY --chown=airflow:root meltano.yml /opt/elt/meltano.yml
RUN meltano install

COPY --chown=airflow:root app /opt/elt/app
COPY --chown=airflow:root dags /opt/airflow/dags