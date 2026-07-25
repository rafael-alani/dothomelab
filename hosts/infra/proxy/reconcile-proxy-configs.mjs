import internalNginx from "/app/internal/nginx.js";
import ProxyHost from "/app/models/proxy_host.js";

const requiredDomains = new Set([
  "immichframe.rafael.media",
  "loki.rafael.media",
  "paperless.rafael.media",
  "paperless-gpt.rafael.media",
  "prometheus.rafael.media",
  "wizarr.rafael.media",
]);

try {
  const rows = await ProxyHost.query()
    .where("is_deleted", 0)
    .withGraphFetched("[owner,certificate,access_list.[clients,items]]");
  const selected = rows.filter((row) =>
    row.domain_names.some((domain) => requiredDomains.has(domain)),
  );
  const found = new Set(selected.flatMap((row) => row.domain_names));
  const missing = [...requiredDomains].filter((domain) => !found.has(domain));
  if (missing.length > 0) {
    throw new Error(`NPM proxy rows are missing: ${missing.join(", ")}`);
  }

  for (const row of selected) {
    await internalNginx.configure(ProxyHost, "proxy_host", row);
    console.log(`Reconciled NPM proxy config ${row.id}: ${row.domain_names.join(",")}`);
  }
} finally {
  await ProxyHost.knex().destroy();
}
