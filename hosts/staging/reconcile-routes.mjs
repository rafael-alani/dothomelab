import internalNginx from "/app/internal/nginx.js";
import ProxyHost from "/app/models/proxy_host.js";

try {
  const rows = await ProxyHost.query()
    .where("is_deleted", 0)
    .withGraphFetched("[owner,certificate,access_list.[clients,items]]");
  const sharedNames = new Set(["analytics.staging.rafael.media", "grafana.staging.rafael.media"]);
  const selected = rows.filter((row) => row.forward_host === "192.168.0.114" ||
    (row.forward_host === "192.168.0.110" && row.domain_names.length === 1 && sharedNames.has(row.domain_names[0])));
  if (!selected.length) throw new Error("No staging proxy routes found");
  for (const row of selected) {
    if (!row.advanced_config.includes("deny all;")) throw new Error("Private ACL missing");
    await internalNginx.configure(ProxyHost, "proxy_host", row);
    console.log(`Configured private staging route ${row.domain_names.join(",")}`);
  }
} finally {
  await ProxyHost.knex().destroy();
}
