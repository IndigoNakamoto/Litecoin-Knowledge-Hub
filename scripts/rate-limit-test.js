import http from 'k6/http';
import { check, sleep } from 'k6';

// Set this to your backend URL (dev or prod) when running:
//   BASE_URL=http://localhost:8000 k6 run rate-limit-test.js
//   BASE_URL=https://api.lite.space k6 run rate-limit-test.js
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const options = {
  vus: 1,          // single virtual user to simulate one IP
  duration: '3m',  // run for 3 minutes
  thresholds: {
    http_req_failed: ['rate<0.5'],                       // no more than 50% failed overall
    'http_req_duration{status:429}': ['p(95)<1000'],     // 429s should be fast
  },
};

export default function () {
  const payload = JSON.stringify({
    query: 'Test rate limiting',
    chat_history: [],
  });

  const params = {
    headers: { 'Content-Type': 'application/json' },
  };

  const res = http.post(`${BASE_URL}/api/v1/chat/stream`, payload, params);

  check(res, {
    'status is 200 or 429': (r) => r.status === 200 || r.status === 429,
  });

  if (res.status === 429) {
    console.log('Hit rate limit:', res.status, res.headers['Retry-After'], res.body);
  }

  // Small sleep to tune requests/sec and avoid pure DoS
  sleep(0.5);
}


