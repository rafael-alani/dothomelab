import internalNginx from "/app/internal/nginx.js";
import ProxyHost from "/app/models/proxy_host.js";

const requiredDomains = new Set([
  "audiobookshelf.rafael.media",
  "bar.rafael.media",
  "bar-api.rafael.media",
  "bar-search.rafael.media",
  "droppedneedle.rafael.media",
  "immichframe.rafael.media",
  "join-stream.rafael.ink",
  "kavita.rafael.media",
  "loki.rafael.media",
  "n8n.rafael.media",
  "paperless.rafael.media",
  "paperless-gpt.rafael.media",
  "pdf.rafael.media",
  "prometheus.rafael.media",
  "pulse.rafael.media",
  "snapotter.rafael.media",
  "slskd.rafael.media",
  "stream.rafael.ink",
  "wizarr.rafael.media",
  "yt-dlp.rafael.media",
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
