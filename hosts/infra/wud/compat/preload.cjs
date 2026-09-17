'use strict';

// APIs verified against the exact image digest in ../compose.yaml.
const root = '/home/node/app';
require('./repairs.cjs').install({
  Custom: require(`${root}/dist/registries/providers/custom/Custom`).default,
  Ghcr: require(`${root}/dist/registries/providers/ghcr/Ghcr`).default,
  Docker: require(`${root}/dist/triggers/providers/docker/Docker`).default,
  axios: require(`${root}/node_modules/axios`).default,
});
