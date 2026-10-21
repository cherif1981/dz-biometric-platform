import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TOKEN    = __ENV.TOKEN;
const ID_IMAGE = __ENV.ID_IMAGE;
const SELFIE   = __ENV.SELFIE;

const verifyErrors  = new Rate('verify_errors');
const verifyLatency = new Trend('verify_latency_ms');

export const options = {
  stages: [
    { duration: '30s', target: 50 },
    { duration: '60s', target: 50 },
    { duration: '15s', target: 0 },
  ],
  thresholds: {
    'http_req_failed': ['rate<0.05'],
    'verify_latency_ms': ['p(95)<1500', 'p(99)<3000'],
  },
};

export default function () {
  if (!TOKEN) {
    const r = http.post(BASE_URL + '/api/v1/verify/');
    check(r, { 'unauth 401': (x) => x.status === 401 });
    sleep(1);
    return;
  }
  const files = {};
  if (ID_IMAGE && SELFIE) {
    files['id_image'] = http.file(open(ID_IMAGE, 'b'), 'id.jpg', 'image/jpeg');
    files['selfie']   = http.file(open(SELFIE,   'b'), 'self.jpg', 'image/jpeg');
  } else {
    files['id_image'] = http.file('FAKE', 'id.jpg', 'image/jpeg');
    files['selfie']   = http.file('FAKE', 'self.jpg', 'image/jpeg');
  }
  const r = http.post(BASE_URL + '/api/v1/verify/', {}, {
    headers: { Authorization: 'Bearer ' + TOKEN },
    files,
  });
  const ok = check(r, {
    'status 200/422/429': (x) => [200, 422, 429].indexOf(x.status) >= 0,
    'no 5xx': (x) => x.status < 500,
  });
  verifyErrors.add(!ok);
  verifyLatency.add(r.timings.duration);
  sleep(0.2 + Math.random() * 0.3);
}