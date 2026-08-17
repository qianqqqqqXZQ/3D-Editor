const { writeFileSync } = require("node:fs");

const origin = (process.env.EDITOR_API_ORIGIN || "").replace(/\/$/, "");

if (origin && !/^https:\/\/[^\s]+$/.test(origin)) {
  throw new Error("EDITOR_API_ORIGIN must be an HTTPS origin without a trailing slash.");
}

writeFileSync(
  "static/runtime-config.js",
  `window.EDITOR_API_BASE = ${JSON.stringify(origin)};\n`,
  "utf8",
);
