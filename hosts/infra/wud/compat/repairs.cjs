'use strict';

// Public pull-only authentication. No user credentials or persisted tokens.
const PUBLIC_REGISTRIES = {
  'https://lscr.io': ['https://ghcr.io/token', 'ghcr.io'],
  'https://registry.gitlab.com': ['https://gitlab.com/jwt/auth', 'container_registry'],
  'https://docker.n8n.io': ['https://auth.docker.io/token', 'registry.docker.io'],
};

function install({ Custom, Ghcr, Docker, axios }) {
  const authenticate = Custom.prototype.authenticate;
  const tokens = new Map();
  Custom.prototype.authenticate = async function (image, options) {
    const endpoint = PUBLIC_REGISTRIES[this.configuration.url];
    if (!endpoint || this.getAuthCredentials()) {
      return authenticate.call(this, image, options);
    }
    const [url, service] = endpoint;
    const scope = `repository:${image.name}:pull`;
    const key = `${url}|${scope}`;
    let entry = tokens.get(key);
    if (!entry || entry.expires <= Date.now()) {
      let response;
      try {
        response = await axios({
          method: 'GET', url, timeout: 15000,
          params: { service, scope },
          headers: { Accept: 'application/json' },
        });
      } catch (error) {
        // Do not put axios request objects or bearer tokens in logs.
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

  // Enforce the Compose label for the existing container too, without
  // recreating cross-seed just to repair its updater. WUD coerces 6-arm64
  // to semver 6 and otherwise selects an incompatible platform manifest.
  const getTags = Ghcr.prototype.getTags;
  Ghcr.prototype.getTags = async function (image) {
    if (image.name === 'cross-seed/cross-seed' && image.tag.value === '6') {
      return ['6'];
    }
    return getTags.call(this, image);
  };

  // The installed WUD resolves followProgress(error), swallowing failures
  // such as ENOSPC, and then stops/recreates the old application image.
  Docker.prototype.pullImage = async function (dockerApi, auth, image, log) {
    log.info(`Pull image ${image}`);
    const stream = await dockerApi.pull(image, { authconfig: auth });
    await new Promise((resolve, reject) => {
      dockerApi.modem.followProgress(stream, (error, events) => {
        const failed = (events || []).find(event => event.error || event.errorDetail?.message);
        if (error || failed) {
          reject(error || new Error(failed.errorDetail?.message || failed.error));
        } else {
          resolve();
        }
      });
    });
    log.info(`Image ${image} pulled with success`);
  };
}

module.exports = { install };
