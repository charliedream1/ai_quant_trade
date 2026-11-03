// File format: JavaScript module; encoding: UTF-8
// Import the installed lexical implementation without loading a vector engine.
import {pathToFileURL} from "node:url";
let input = "";
for await (const part of process.stdin) input += part;
const request = JSON.parse(input);
const {runRgSearch} = await import(pathToFileURL(request.module).href);
const result = await runRgSearch({
  root: request.root, paths: request.paths, patterns: request.keywords,
  noIgnore: true, hidden: true, limit: request.limit,
  rgOptions: {fixedStrings: true, ignoreCase: true, extraArgs: ["--max-count", String(request.matches_per_file)]}
});
process.stdout.write(JSON.stringify(result));
