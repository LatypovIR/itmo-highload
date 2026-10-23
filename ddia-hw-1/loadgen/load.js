import http from 'k6/http';
import exec from 'k6/execution';

const targets = __ENV.TARGET_URLS.split(',');
const params = { headers: { 'Content-Type': 'application/json' }, timeout: '200ms' };
const TIMEOUT_ERROR = 1050;
const TIMEOUT_WINDOW = 20;

http.setResponseCallback(http.expectedStatuses({ min: 200, max: 499 }, 503));

export const options = {
  scenarios: {
    staircase: {
      executor: 'ramping-arrival-rate',
      startRate: 50,
      preAllocatedVUs: 50,
      maxVUs: 2000,
      stages: Array.from({ length: 40 }, (_, step) => [
        { target: 50 + 500 * step, duration: '1s' },
        { target: 50 + 500 * step, duration: '9s' },
      ]).flat(),
    },
  },
};

const recentTimeouts = [];
const lastId = {};

const randomInt = (max) => 1 + Math.floor(Math.random() * max);

function trackTimeouts(res) {
  recentTimeouts.push(res.error_code === TIMEOUT_ERROR);
  if (recentTimeouts.length > TIMEOUT_WINDOW) recentTimeouts.shift();
  if (recentTimeouts.filter(Boolean).length >= TIMEOUT_WINDOW / 2) exec.test.abort('mass timeouts');
}

function orderBody() {
  const quantity = Math.random() < 0.03 ? 0 : randomInt(10);
  return JSON.stringify({ customer_id: `customer-${randomInt(1000)}`, items: [{ sku: `sku-${randomInt(500)}`, quantity }] });
}

function request(target) {
  const roll = Math.random();
  if (roll < 0.15) return http.get(`${target}/orders?limit=${randomInt(100)}`, params);
  if (roll < 0.45 || !lastId[target]) {
    const res = http.post(`${target}/orders`, orderBody(), params);
    if (res.status === 201) lastId[target] = Math.max(lastId[target] || 0, res.json('id'));
    return res;
  }
  const id = Math.random() < 0.05 ? 0 : randomInt(lastId[target]);
  if (roll < 0.8) return http.get(http.url`${target}/orders/${id}`, params);
  return http.put(http.url`${target}/orders/${id}`, orderBody(), params);
}

export default function () {
  trackTimeouts(request(targets[Math.floor(Math.random() * targets.length)]));
}
