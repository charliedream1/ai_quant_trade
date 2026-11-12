// File format: JavaScript CommonJS; encoding: UTF-8
// Decode the existing login with WorkBuddy's native codec, only into parent memory.
const path = require("node:path");
const fs = require("node:fs");
const [installation, authentication] = process.argv.slice(2);
const root = path.join(installation, "resources", "app.asar", "main");
let transport = require(path.join(root, "dist.js"));
let decode;
if (typeof transport.s === "function" && typeof transport.T === "function") {
  transport.s();
  decode = transport.T;
} else {
  // Current WorkBuddy exports native bootstrap normalization from src.js.
  transport = require(path.join(root, "src.js"));
  transport.t();
  decode = transport._;
}
if (typeof decode !== "function") throw Error("Unsupported WorkBuddy credential codec");
const material = decode(process._linkedBinding("electron_browser_workbuddy_storage").loggerGet());
if (material.symmetric.status !== "available") throw Error("Desktop credential key unavailable");
const protection = require(path.join(root, "credential-protection.js"));
protection.t();
protection._({policy:"fields", symmetricKey:material.symmetric.value, asymmetricUnavailable:"missing-key"});
const codec = protection.v({purpose:"workbuddy-auth-session", resourceId:"auth/"+path.basename(authentication)});
try {
  const result = codec.decode(JSON.parse(fs.readFileSync(authentication,"utf8")), protection.l);
  process.stdout.write(JSON.stringify(result.value));
} finally { codec.dispose(); protection.b(); }
