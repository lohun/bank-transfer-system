const { faker } = require("@faker-js/faker");
const http = require("http");
const fs = require("fs");
const path = require("path");

const JSON_PATH = path.join(__dirname, "accounts.json");
const NUM_ACCOUNTS = 100;
const BASE_HOST = "localhost";
const BASE_PORT = 8080;

function createAccount(owner_name, initial_balance) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({ owner_name, initial_balance });

    const options = {
      hostname: BASE_HOST,
      port: BASE_PORT,
      path: "/accounts",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(postData),
      },
    };

    const req = http.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => {
        data += chunk;
      });
      res.on("end", () => {
        if (res.statusCode === 201) {
          resolve(JSON.parse(data));
        } else {
          reject(new Error(`Failed with status ${res.statusCode}: ${data}`));
        }
      });
    });

    req.on("error", (e) => reject(e));
    req.write(postData);
    req.end();
  });
}

async function main() {
  const accounts = [];
  for (let i = 0; i < NUM_ACCOUNTS; i++) {
    const owner_name = faker.person.fullName();
    const balance = parseFloat(faker.finance.amount({ min: 100, max: 5000, dec: 2 }));

    try {
      const account = await createAccount(owner_name, balance);
      accounts.push(account);
      process.stdout.write(".");
    } catch (err) {
      console.error(`\nError creating account: ${err.message}`);
    }
  }

  fs.writeFileSync(JSON_PATH, JSON.stringify(accounts, null, 2));
  console.log(`\nSeeded ${accounts.length} accounts → ${JSON_PATH}`);
}

main().catch(console.error);
