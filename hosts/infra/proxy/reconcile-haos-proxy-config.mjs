import internalNginx from "/app/internal/nginx.js";
import ProxyHost from "/app/models/proxy_host.js";

try {
  const rows = await ProxyHost.query()
    .where("is_deleted", 0)
    .withGraphFetched("[owner,certificate,access_list.[clients,items]]");
  const selected = rows.filter(
    (row) =>
      row.domain_names.length === 1 &&
      row.domain_names[0] === "ha.rafael.media",
  );
  if (selected.length !== 1) {
    throw new Error(
      `Expected one active ha.rafael.media proxy row, found ${selected.length}`,
    );
  }

  await internalNginx.configure(ProxyHost, "proxy_host", selected[0]);
  console.log(`Reconciled NPM proxy config ${selected[0].id}: ha.rafael.media`);
} finally {
  await ProxyHost.knex().destroy();
}
