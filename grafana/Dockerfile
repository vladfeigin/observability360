FROM grafana/grafana:11.4.0
RUN grafana-cli plugins install grafana-azure-data-explorer-datasource

COPY grafana.ini /etc/grafana/
COPY provisioning /etc/grafana/provisioning