'use strict';

const PUBLIC_REGISTRIES = {
  'https://lscr.io': ['https://ghcr.io/token', 'ghcr.io'],
  'https://registry.gitlab.com': ['https://gitlab.com/jwt/auth', 'container_registry'],
};

function install({ Ghcr, Custom, Hub, axios }) {
  // n8n publishes beta releases under plain numeric Docker tags. Semver alone
  // cannot identify stable releases; GitHub's latest endpoint excludes prereleases.
  const hubTags = Hub.prototype.getTags;
  Hub.prototype.getTags = async function (image) {
    if (image.name !== 'n8nio/n8n') return hubTags.call(this, image);
    let response;
    try {
      response = await axios({ method: 'GET',
        url: 'https://api.github.com/repos/n8n-io/n8n/releases/latest',
        timeout: 15000, headers: { Accept: 'application/vnd.github+json',
          'User-Agent': 'dothomelab-wud' } });
    } catch (error) {
      throw new Error(`n8n stable release lookup failed: ${error.response?.status || error.code || 'network error'}`);
    }
    const release = response.data;
    const match = /^n8n@(\d+\.\d+\.\d+)$/.exec(release?.tag_name || '');
    if (!match || release.prerelease !== false || release.draft !== false) {
      throw new Error('Invalid n8n stable release metadata');
    }
    return [match[1]]; // Compose's major-version filter still applies.
  };
  // These public aliases need an image-scoped token; the root /v2/ challenge
  // does not reliably supply one. Native 9.7 auth still returns LSCR 401s.
  const authenticate = Custom.prototype.authenticate;
  const tokens = new Map();
  Custom.prototype.authenticate = async function (image, options) {
    const endpoint = PUBLIC_REGISTRIES[this.configuration.url];
    if (!endpoint || this.getAuthCredentials()) return authenticate.call(this, image, options);
    const [url, service] = endpoint;
    const scope = `repository:${image.name}:pull`;
    const key = `${url}|${scope}`;
    let entry = tokens.get(key);
    if (!entry || entry.expires <= Date.now()) {
      let response;
      try {
        response = await axios({ method: 'GET', url, timeout: 15000,
          params: { service, scope }, headers: { Accept: 'application/json' } });
      } catch (error) {
        throw new Error(`Public registry token request failed: ${error.response?.status || error.code || 'network error'}`);
      }
      const token = response.data.token || response.data.access_token;
      if (!token) throw new Error('Public registry returned no pull token');
      const lifetime = Math.max(0, Math.min(60, Number(response.data.expires_in) || 60) - 10);
      entry = { token, expires: Date.now() + lifetime * 1000 };
      tokens.set(key, entry);
    }
    return { ...options, headers: { ...options.headers, Authorization: `Bearer ${entry.token}` } };
  };
  // The retained cross-seed runtime predates its Compose tag constraint.
  const getTags = Ghcr.prototype.getTags;
  Ghcr.prototype.getTags = async function (image) {
    if (image.name === 'cross-seed/cross-seed' && image.tag.value === '6') return ['6'];
    return getTags.call(this, image);
  };
}

module.exports = { install };
