const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

// Execute application source while substituting only external I/O in tests.
function load(relative, imports = {}, fetch = async () => new Response(null, { status: 200 })) {
  const source = fs.readFileSync(path.join(__dirname, "..", relative), "utf8");
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(compiled, {
    module, exports: module.exports,
    require: (name) => {
      if (name in imports) return imports[name];
      if (name.startsWith("@/")) return load(name.slice(2) + ".ts", imports, fetch);
      if (name.startsWith(".")) return load(path.join(path.dirname(relative), name) + ".ts", imports, fetch);
      return require(name);
    },
    URL, URLSearchParams, Request, Response, Headers, AbortSignal, fetch, btoa,
    crypto: require("node:crypto").webcrypto,
    process: { env: { NEXT_PUBLIC_API_BASE_URL: "http://api.fixture/v1" } },
  }, { filename: relative });
  return module.exports;
}

module.exports = { load };
