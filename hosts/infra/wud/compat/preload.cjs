'use strict';

require('./repairs.cjs').install({
  Custom: require('/home/node/app/dist/registries/providers/custom/Custom').default,
  Ghcr: require('/home/node/app/dist/registries/providers/ghcr/Ghcr').default,
  Hub: require('/home/node/app/dist/registries/providers/hub/Hub').default,
  axios: require('/home/node/app/node_modules/axios').default,
});
