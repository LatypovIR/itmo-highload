// Каркас сценария k6. Профиль нагрузки (разгон, удержание, доля ошибок) — ваша часть.
import http from 'k6/http';
import { check } from 'k6';

const targets = __ENV.TARGET_URLS.split(',');

export const options = {
  vus: 1,
  iterations: 1,
};

export default function () {
  for (const target of targets) {
    const res = http.get(`${target}/health`);
    check(res, { [`${target} is healthy`]: (r) => r.status === 200 });
  }
}
