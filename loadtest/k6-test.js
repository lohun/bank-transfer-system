import http from "k6/http";
import { check } from "k6";

const accounts = JSON.parse(open("./accounts.json"));
const BASE = "http://localhost:8080";
const ITERS_PER_VU = Math.ceil(accounts.length / 25);

export const options = {
  vus: 25,
  iterations: accounts.length,
  noConnectionReuse: true,
};

export default function () {
  const idx = (__VU - 1) * ITERS_PER_VU + __ITER;
  const accountId = idx + 1;
  const CREDIT_AMOUNT = 25.50;
  const DEBIT_AMOUNT = 10.00;

  const requests = [];
  for (let i = 0; i < 150; i++) {
    requests.push(["POST", `${BASE}/credit`, JSON.stringify({ account_id: accountId, amount: CREDIT_AMOUNT }), { headers: { "Content-Type": "application/json" } }]);
    requests.push(["POST", `${BASE}/debit`, JSON.stringify({ account_id: accountId, amount: DEBIT_AMOUNT }), { headers: { "Content-Type": "application/json" } }]);
  }

  const responses = http.batch(requests);
  for (const res of responses) {
    check(res, {
      "queued (202)": (r) => r.status === 202,
    });
  }
}
