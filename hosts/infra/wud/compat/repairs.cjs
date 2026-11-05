'use strict';

function install({ Ghcr }) {
  // The retained cross-seed runtime predates its Compose tag constraint.
  const getTags = Ghcr.prototype.getTags;
  Ghcr.prototype.getTags = async function (image) {
    if (image.name === 'cross-seed/cross-seed' && image.tag.value === '6') return ['6'];
    return getTags.call(this, image);
  };
}

module.exports = { install };
