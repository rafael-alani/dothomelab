// Run only through Infra's root-operated route reconciler, inside NPM.
// Credentials stay in NPM's existing recovery data; never return certificate meta.
import fs from 'node:fs';
import certificateModel from '/app/models/certificate.js';
import internalCertificate from '/app/internal/certificate.js';

const domains = ['*.staging.rafael.media', 'staging.rafael.media'];
try {
  const certificates = await certificateModel.query().where('is_deleted', 0);
  let certificate = certificates.find(c => domains.every(d => c.domain_names.includes(d)));
  if (!certificate) {
    const source = certificates.find(c => c.domain_names.includes('*.rafael.media')
      && c.provider === 'letsencrypt' && c.meta?.dns_challenge
      && c.meta?.dns_provider === 'cloudflare' && c.meta?.dns_provider_credentials);
    if (!source) throw new Error('Existing Cloudflare DNS-01 recovery credentials are required');
    const access = {
      can: async () => ({permission_visibility: 'all'}),
      token: {getUserId: () => source.owner_user_id},
    };
    const meta = Object.fromEntries(
      ['dns_challenge', 'dns_provider', 'dns_provider_credentials', 'propagation_seconds']
        .filter(k => source.meta[k] !== undefined).map(k => [k, source.meta[k]])
    );
    certificate = await internalCertificate.create(access, {
      provider: 'letsencrypt', domain_names: domains, meta,
    });
  }
  if (!fs.existsSync(`/etc/letsencrypt/live/npm-${certificate.id}/fullchain.pem`)) {
    throw new Error('Staging wildcard certificate files are missing from recovery data');
  }
  console.log(JSON.stringify({id: certificate.id, domains}));
} catch {
  // Do not echo provider errors: they may contain credential-bearing arguments.
  console.error('Staging certificate reconciliation failed; inspect NPM privately');
  process.exitCode = 1;
} finally {
  await certificateModel.knex().destroy();
}
