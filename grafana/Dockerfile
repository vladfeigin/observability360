FROM --platform=linux/amd64 grafana/grafana:11.4.0
RUN grafana-cli plugins install grafana-azure-data-explorer-datasource

COPY --chown=grafana grafana.ini /etc/grafana/ 
COPY --chown=grafana provisioning /etc/grafana/provisioning