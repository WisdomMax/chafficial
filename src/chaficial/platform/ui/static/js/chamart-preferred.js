/* Direct-stock identity only. Paid/priority exposure alone never earns this badge. */
(function (root) {
  function isOwned(vehicle) {
    if (!vehicle || ['SOLD', 'SOLD_CONFIRMED'].includes(String(vehicle.status || '').toUpperCase())) return false;
    const type = String(vehicle.listing_ownership_type || vehicle.ownership_type || '').toUpperCase();
    if (type) return type === 'OWNED' || type === 'CHAMART_OWNED';
    return vehicle.is_chamart_owned === true || vehicle.is_chamart_owned === 1;
  }
  function compareOwned(a, b) { return Number(isOwned(b)) - Number(isOwned(a)); }
  function badge(vehicle) {
    return isOwned(vehicle) ? '<img class="cm-preferred-sticker" src="/static/img/chamart-preferred.svg" alt="차마트 우대차량" title="차마트 직접 보유 차량" width="148" height="30">' : '';
  }
  root.ChamartPreferred = { isOwned, compareOwned, badge };
})(typeof window !== 'undefined' ? window : globalThis);
