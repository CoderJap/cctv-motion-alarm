const fs = require("fs");
const input = fs.readFileSync(0, "utf8").trim();

console.log("Hello from Codella!");
console.log("Input:", input || "(empty)");