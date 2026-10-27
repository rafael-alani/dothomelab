import nginx from '/app/internal/nginx.js';
import ProxyHost from '/app/models/proxy_host.js';
const allowed = new Set([
  'analytics.rafael.media', 'grafana.rafael.media', 'prometheus.rafael.media', 'loki.rafael.media',
  'analytics.staging.rafael.media', 'grafana.staging.rafael.media',
  'blog.staging.rafael.media', 'rafael.ink',
]);
try {
  const row = await ProxyHost.query().findById(ROUTE_ID)
    .withGraphFetched('[owner,certificate,access_list.[clients,items]]');
  if (!row || row.domain_names.length !== 1 || !allowed.has(row.domain_names[0])) {
    throw new Error('Observability route ownership mismatch');
  }
  await nginx.configure(ProxyHost, 'proxy_host', row);
} finally {
  await ProxyHost.knex().destroy();
}
