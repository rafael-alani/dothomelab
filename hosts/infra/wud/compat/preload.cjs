'use strict';

require('./repairs.cjs').install({
  Ghcr: require('/home/node/app/dist/registries/providers/ghcr/Ghcr').default,
});
