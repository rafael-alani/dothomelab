import nginx from '/app/internal/nginx.js';
import ProxyHost from '/app/models/proxy_host.js';
try {
  const row = await ProxyHost.query().findById(ROUTE_ID)
    .withGraphFetched('[owner,certificate,access_list.[clients,items]]');
  if (!row || JSON.stringify(row.domain_names) !== '["rafael.ink"]') throw new Error('Apex mismatch');
  await nginx.configure(ProxyHost, 'proxy_host', row);
} finally {
  await ProxyHost.knex().destroy();
}
