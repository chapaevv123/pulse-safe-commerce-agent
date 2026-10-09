let current = null;
const $ = id => document.getElementById(id);

const render = d => {
  current = d;
  $('parsed').innerHTML = `<b>${d.intent.amount} ${d.intent.currency}</b><br>${d.intent.recipient_label}<br>${d.intent.purpose}<br><small>Source: ${d.intent.provider} · confidence ${d.intent.confidence}</small>`;
  const policy = d.trace.find(x => x.stage === 'POLICY');
  $('policy').innerHTML = policy ? `<b class="${policy.status === 'PASS' ? 'safe-text' : 'blocked'}">${policy.status}</b><br>${policy.reason_code}<br>${policy.decision}` : 'Not evaluated';
  $('approve').disabled = d.status !== 'AWAITING_APPROVAL';
  $('create').disabled = d.status !== 'APPROVED';
  $('capture').disabled = d.status !== 'PAYPAL_ORDER_CREATED';
  $('mutate').disabled = d.status !== 'PAYPAL_ORDER_CREATED';
  $('replay').disabled = d.status !== 'SUCCEEDED';
  $('reconcile').disabled = !d.paypal_order_id;
  $('execution-state').innerHTML = `<b class="${d.status === 'SUCCEEDED' ? 'safe-text' : d.status === 'FAILED' ? 'blocked' : ''}">${d.status}</b>${d.paypal_status ? ' / ' + d.paypal_status : ''}${d.paypal_order_id ? '<br>Order ' + d.paypal_order_id : ''}`;
  $('receipt').textContent = d.receipt ? JSON.stringify(d.receipt, null, 2) : `${d.status}${d.error_code ? ' · ' + d.error_code : ''}`;
  $('reconciliation').textContent = d.reconciliation ? `Reconciliation: ${d.reconciliation.result} · PayPal ${d.reconciliation.paypal_status}` : '';
  $('trace').innerHTML = d.trace.map(x => `<article><b>${x.stage}</b><br>${x.status}<br><small>${x.reason_code}<br>${x.created_at}</small></article>`).join('');
};

const call = async (url, options = {}) => {
  const response = await fetch(url, {headers: {'Content-Type': 'application/json'}, ...options});
  const data = await response.json();
  if (!response.ok) throw Error(data.detail || 'Request failed');
  return data;
};

const showBanner = (kind, message) => {
  const banner = $('payment-banner');
  banner.className = `payment-banner ${kind}`;
  banner.textContent = message;
};

document.querySelectorAll('[data-intent]').forEach(button => button.onclick = () => {$('intent').value = button.dataset.intent;});
$('propose').onclick = async () => {try {render(await call('/api/intents', {method: 'POST', body: JSON.stringify({text: $('intent').value, max_single_payment: $('limit').value})}));} catch (error) {$('parsed').textContent = error.message;}};
$('approve').onclick = async () => render(await call(`/api/payments/${current.request_id}/approve`, {method: 'POST'}));
$('create').onclick = async () => {const data = await call(`/api/payments/${current.request_id}/paypal-order`, {method: 'POST'}); render(data); if (data.approval_url) {$('checkout').href = data.approval_url; $('checkout').classList.remove('hidden');}};
$('capture').onclick = async () => render(await call(`/api/payments/${current.request_id}/execute`, {method: 'POST', body: '{}'}));
$('mutate').onclick = async () => render(await call(`/api/payments/${current.request_id}/execute`, {method: 'POST', body: JSON.stringify({amount_override: '29.50'})}));
$('replay').onclick = async () => render(await call(`/api/payments/${current.request_id}/execute`, {method: 'POST', body: '{}'}));
$('reconcile').onclick = async () => {const result = await call(`/api/payments/${current.request_id}/reconcile`, {method: 'POST'}); $('reconciliation').textContent = `Reconciliation: ${result.result} · PayPal ${result.paypal_status}`;};

(async () => {
  const query = new URLSearchParams(location.search);
  const requestId = query.get('request_id');
  const payment = query.get('payment');
  if (!requestId) return;
  try {
    const data = await call(`/api/payments/${encodeURIComponent(requestId)}`);
    render(data);
    if (payment === 'success') showBanner('success', 'PayPal Sandbox payment completed successfully.');
    else if (payment === 'cancelled') showBanner('cancelled', 'PayPal Sandbox payment was cancelled. No payment was captured.');
    else if (payment === 'error') showBanner('error', `PayPal Sandbox payment could not be completed. ${data.error_code || 'PAYPAL_RETURN_FAILED'}`);
  } catch (_) {
    showBanner('error', 'Payment state could not be restored safely.');
  }
})();
