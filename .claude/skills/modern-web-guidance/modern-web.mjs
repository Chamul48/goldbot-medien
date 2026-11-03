#!/usr/bin/env node

// src/cli/modern-web.ts
import { parseArgs } from "node:util";
import { spawnSync } from "node:child_process";
import { join as join2, dirname as dirname2, basename } from "node:path";
import { existsSync as existsSync3, fstatSync, readFileSync as readFileSync3, readdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";

// src/rag/guides.ts
import { promises as fs, readFileSync, existsSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";
var BUNDLE_DIR = path.dirname(fileURLToPath(import.meta.url));
function resolveSkillsCliDataDir() {
  if (existsSync(path.join(BUNDLE_DIR, "guides.json")) || existsSync(path.join(BUNDLE_DIR, "use-cases.vectors.gen.json.gz"))) {
    return BUNDLE_DIR;
  }
  let dir = BUNDLE_DIR;
  while (dir !== path.dirname(dir)) {
    if (existsSync(path.join(dir, "pnpm-lock.yaml"))) {
      return path.join(dir, "out/build/skills-cli");
    }
    dir = path.dirname(dir);
  }
  return BUNDLE_DIR;
}
function loadUseCases() {
  const dataDir = resolveSkillsCliDataDir();
  const guidesJsonPath = path.join(dataDir, "guides.json");
  if (!existsSync(guidesJsonPath)) {
    throw new Error(`guides.json not found at ${guidesJsonPath}. Run 'pnpm build' first.`);
  }
  return JSON.parse(readFileSync(guidesJsonPath, "utf-8"));
}
var USE_CASES = loadUseCases();
function getUseCase(useCaseId) {
  return USE_CASES.find((u) => u.id === useCaseId);
}
async function getGuide(useCaseId) {
  const useCase = getUseCase(useCaseId);
  if (!useCase) return null;
  const dataDir = resolveSkillsCliDataDir();
  const filePath = path.join(dataDir, "guides", useCase.category, `${useCaseId}.md`);
  try {
    const content = await fs.readFile(filePath, "utf-8");
    return content;
  } catch (error) {
    if (error.code === "ENOENT") {
      return null;
    }
    throw error;
  }
}

// src/rag/logger.ts
import { appendFileSync } from "fs";
import path2 from "path";

// src/core/constants.ts
var MODERN_WEB_LOG_FILE = "modern-web.log";

// src/rag/logger.ts
function logToolResult(toolName, result) {
  if (process.env.ENABLE_FILE_LOGGING !== "true") {
    return;
  }
  try {
    const logDir = process.env.MODERN_WEB_LOG_DIR || process.cwd();
    const logPath = path2.join(logDir, MODERN_WEB_LOG_FILE);
    const logEntry = {
      timestamp: (/* @__PURE__ */ new Date()).toISOString(),
      tool: toolName,
      result
    };
    appendFileSync(logPath, JSON.stringify(logEntry) + "\n", "utf8");
  } catch (err) {
    console.error("Failed to log tool result:", err);
  }
}

// src/core/mwgrc.ts
import fs2 from "node:fs";
import path3 from "node:path";
var CONFIG_FILENAME = ".mwgrc";
function resolveMwgrcPath(startDir = process.cwd()) {
  let dir = path3.resolve(startDir);
  while (true) {
    if (fs2.existsSync(path3.join(dir, CONFIG_FILENAME)) || fs2.existsSync(path3.join(dir, ".git"))) {
      return path3.join(dir, CONFIG_FILENAME);
    }
    const parent = path3.dirname(dir);
    if (parent === dir) return path3.join(path3.resolve(startDir), CONFIG_FILENAME);
    dir = parent;
  }
}
function isNodeError(e) {
  return typeof e === "object" && e !== null && "code" in e;
}
function readMwgrc(startDir = process.cwd()) {
  return readMwgrcFile(resolveMwgrcPath(startDir));
}
function readMwgrcFile(filePath) {
  let parsed;
  try {
    parsed = JSON.parse(fs2.readFileSync(filePath, "utf8"));
  } catch (e) {
    if (isNodeError(e) && e.code === "ENOENT") return {};
    throw new Error(`Invalid ${CONFIG_FILENAME} at ${filePath}: ${e.message}`);
  }
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error(`Invalid ${CONFIG_FILENAME} at ${filePath}: expected a JSON object`);
  }
  return parsed;
}
function writeMwgrc(patch, startDir = process.cwd()) {
  const targetPath = resolveMwgrcPath(startDir);
  const existing = readMwgrcFile(targetPath);
  fs2.writeFileSync(targetPath, JSON.stringify({ ...existing, ...patch }, null, 2) + "\n", "utf8");
  return targetPath;
}

// src/rag/retrieve.ts
var OriginTrialGateError = class extends Error {
  constructor(message) {
    super(message);
    this.name = "OriginTrialGateError";
  }
};
function formatOriginTrialGateMessage(guideId, originTrials) {
  const featureIds = originTrials.map((ot) => ot.id).filter(Boolean).join(", ");
  const uniqueUrls = [...new Set(originTrials.map((ot) => ot.chromestatus_url).filter(Boolean))].join(", ");
  const urlSuffix = uniqueUrls ? ` (${uniqueUrls})` : "";
  return `> [!CAUTION]
>
> **Origin Trial features MUST be explicitly authorized by a direct user request.** Never enable Origin Trial guidance or implement experimental Origin Trial APIs (${featureIds}) autonomously (i.e., do not attempt to bypass this gate or write Origin Trial code from memory unless the user has explicitly opted in).
>
> Guide \`${guideId}\` depends on an active Origin Trial${urlSuffix}, which is experimental, subject to change, and requires manual token registration.
>
> Ask the user if they want to opt in to Origin Trial guidance for this project. To authorize it, the user must run this command themselves in their terminal:
>
> \`\`\`sh
> npx modern-web-guidance@latest set-allow-origin-trials
> \`\`\``;
}
async function retrieveUseCase(useCaseId, options) {
  const useCase = getUseCase(useCaseId);
  if (!useCase) {
    throw new Error(`No guide found for use case: ${useCaseId}`);
  }
  const originTrials = useCase.originTrials ?? [];
  if (originTrials.length > 0 && readMwgrc(options?.cwd).allowOriginTrials !== true) {
    throw new OriginTrialGateError(formatOriginTrialGateMessage(useCaseId, originTrials));
  }
  const guide = await getGuide(useCaseId);
  if (!guide) {
    throw new Error(`No guide found for use case: ${useCaseId}`);
  }
  logToolResult("get_best_practices", [{ id: useCaseId }]);
  return guide;
}

// src/cli/set-allow-origin-trials.ts
import * as readline from "node:readline/promises";

// src/cli/telemetry/detect-agent.ts
import { accessSync, constants } from "node:fs";
var DEVIN_LOCAL_PATH = "/opt/.devin";
var KNOWN_AGENTS = {
  CURSOR: "cursor",
  CURSOR_CLI: "cursor-cli",
  CLAUDE: "claude",
  COWORK: "cowork",
  DEVIN: "devin",
  REPLIT: "replit",
  GEMINI: "gemini",
  CODEX: "codex",
  ANTIGRAVITY: "antigravity",
  AUGMENT_CLI: "augment-cli",
  OPENCODE: "opencode",
  GITHUB_COPILOT: "github-copilot",
  V0: "v0"
};
function pathExists(path4) {
  try {
    accessSync(path4, constants.F_OK);
    return true;
  } catch {
    return false;
  }
}
function determineAgent(env = process.env, exists = pathExists) {
  if (env.AI_AGENT) {
    const name = env.AI_AGENT.trim();
    if (name) {
      if (name.startsWith("github_copilot")) {
        return {
          isAgent: true,
          agent: { name: KNOWN_AGENTS.GITHUB_COPILOT }
        };
      }
      const known = Object.values(KNOWN_AGENTS).sort((a, b) => b.length - a.length).find((a) => name.startsWith(a));
      return {
        isAgent: true,
        agent: { name: known ?? name }
      };
    }
  }
  if (env.CURSOR_TRACE_ID) {
    return { isAgent: true, agent: { name: KNOWN_AGENTS.CURSOR } };
  }
  if (env.CURSOR_AGENT || env.CURSOR_EXTENSION_HOST_ROLE === "agent-exec") {
    return { isAgent: true, agent: { name: KNOWN_AGENTS.CURSOR_CLI } };
  }
  if (env.GEMINI_CLI) {
    return { isAgent: true, agent: { name: KNOWN_AGENTS.GEMINI } };
  }
  if (env.CODEX_SANDBOX || env.CODEX_CI || env.CODEX_THREAD_ID) {
    return { isAgent: true, agent: { name: KNOWN_AGENTS.CODEX } };
  }
  if (env.ANTIGRAVITY_AGENT) {
    return { isAgent: true, agent: { name: KNOWN_AGENTS.ANTIGRAVITY } };
  }
  if (env.AUGMENT_AGENT) {
    return { isAgent: true, agent: { name: KNOWN_AGENTS.AUGMENT_CLI } };
  }
  if (env.OPENCODE_CLIENT) {
    return { isAgent: true, agent: { name: KNOWN_AGENTS.OPENCODE } };
  }
  if (env.CLAUDECODE || env.CLAUDE_CODE) {
    if (env.CLAUDE_CODE_IS_COWORK) {
      return { isAgent: true, agent: { name: KNOWN_AGENTS.COWORK } };
    }
    return { isAgent: true, agent: { name: KNOWN_AGENTS.CLAUDE } };
  }
  if (env.REPL_ID) {
    return { isAgent: true, agent: { name: KNOWN_AGENTS.REPLIT } };
  }
  if (env.COPILOT_MODEL || env.COPILOT_ALLOW_ALL || env.COPILOT_GITHUB_TOKEN) {
    return { isAgent: true, agent: { name: KNOWN_AGENTS.GITHUB_COPILOT } };
  }
  if (exists(DEVIN_LOCAL_PATH)) {
    return { isAgent: true, agent: { name: KNOWN_AGENTS.DEVIN } };
  }
  return { isAgent: false, agent: void 0 };
}

// src/cli/set-allow-origin-trials.ts
async function defaultAskConfirmation(targetPath) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
  try {
    const answer = await rl.question(`Enable experimental Origin Trial guidance for this project (${targetPath})? [y/N] `);
    return /^y(es)?$/i.test(answer.trim());
  } finally {
    rl.close();
  }
}
async function handleSetAllowOriginTrials(opts = {}) {
  const detected = determineAgent();
  const isAgent = opts.isAgent ?? detected.isAgent;
  const isTTY = opts.isTTY ?? Boolean(process.stdin.isTTY);
  if (isAgent || !isTTY) {
    const reason = isAgent ? `detected agent environment${detected.agent?.name ? `: ${detected.agent.name}` : ""}` : "non-interactive stdin";
    console.error(
      `Error: \`set-allow-origin-trials\` must be run interactively by a human developer, not an AI agent (${reason}).
Ask the developer to run \`npx modern-web-guidance@latest set-allow-origin-trials\` in their own terminal.
If your IDE terminal sets agent environment variables, run the command in an external terminal.`
    );
    return 1;
  }
  const targetPath = resolveMwgrcPath(opts.cwd);
  const ask = opts.askConfirmation ?? defaultAskConfirmation;
  const confirmed = await ask(targetPath);
  if (!confirmed) {
    console.log("Aborted.");
    return 1;
  }
  writeMwgrc({ allowOriginTrials: true }, opts.cwd);
  console.log(`Enabled Origin Trial guidance in ${targetPath}. Commit this file to share the opt-in.`);
  return 0;
}

// src/cli/telemetry/clearcut-logger.ts
import process2 from "node:process";

// src/cli/telemetry/watchdog-client.ts
import { spawn } from "node:child_process";
import { fileURLToPath as fileURLToPath2 } from "node:url";
var WatchdogClient = class {
  #childProcess = null;
  #config;
  constructor(config) {
    this.#config = config;
  }
  #ensureProcess() {
    if (this.#childProcess) {
      return this.#childProcess;
    }
    const watchdogPath = fileURLToPath2(
      new URL("./watchdog/main.js", import.meta.url)
    );
    const args = [watchdogPath];
    if (this.#config.clearcutEndpoint) {
      args.push(`--clearcut-endpoint=${this.#config.clearcutEndpoint}`);
    }
    if (this.#config.clearcutIncludePidHeader) {
      args.push("--clearcut-include-pid-header");
    }
    this.#childProcess = spawn(process.execPath, args, {
      stdio: ["pipe", "ignore", "ignore"],
      detached: true
    });
    this.#childProcess.unref();
    this.#childProcess.on("error", () => {
    });
    this.#childProcess.on("exit", () => {
    });
    return this.#childProcess;
  }
  send(message) {
    const childProcess = this.#ensureProcess();
    if (childProcess.stdin && !childProcess.stdin.destroyed && childProcess.pid) {
      try {
        const line = JSON.stringify(message) + "\n";
        childProcess.stdin.write(line);
      } catch {
      }
    }
  }
};

// src/cli/telemetry/types.ts
var CommandType = {
  UNSPECIFIED: 0,
  INSTALL: 1,
  INSTALL_CHOOSE: 2,
  UPDATE: 3,
  UNINSTALL: 4,
  LIST: 5
};
var OsType = {
  UNSPECIFIED: 0,
  WINDOWS: 1,
  MACOS: 2,
  LINUX: 3
};
var WatchdogMessageType = {
  LOG_EVENT: "log-event"
};

// src/cli/version.ts
import { readFileSync as readFileSync2, existsSync as existsSync2 } from "node:fs";
import { join, dirname } from "node:path";
function getVersion(importMetaDirname) {
  const bundlePkgPath = join(importMetaDirname, "../../package.json");
  if (existsSync2(bundlePkgPath)) {
    try {
      const pkg = JSON.parse(readFileSync2(bundlePkgPath, "utf8"));
      if (pkg.version) return pkg.version;
    } catch {
    }
  }
  let dir = importMetaDirname;
  while (dir !== dirname(dir)) {
    const candidate = join(dir, "package.json");
    if (existsSync2(candidate)) {
      try {
        const pkg = JSON.parse(readFileSync2(candidate, "utf8"));
        if (pkg.version) return pkg.version;
      } catch {
      }
    }
    dir = dirname(dir);
  }
  throw new Error(`Could not find package.json with a valid version from ${importMetaDirname}`);
}

// src/cli/telemetry/clearcut-logger.ts
function isTelemetryEnabled() {
  const optOutSetting = process2.env.DISABLE_TELEMETRY?.toLowerCase();
  if (optOutSetting === "1" || optOutSetting === "true") {
    return false;
  }
  if (process2.env.NODE_TEST_CONTEXT !== void 0) {
    return false;
  }
  return true;
}
function detectOS() {
  const platform = process2.platform;
  if (platform === "darwin") return OsType.MACOS;
  if (platform === "win32") return OsType.WINDOWS;
  if (platform === "linux") return OsType.LINUX;
  return OsType.UNSPECIFIED;
}
var LATENCY_BUCKETS = [5, 15, 50, 100, 250, 500, 1e3, 2500, 5e3, 1e4];
function bucketizeLatency(latencyMs) {
  for (const bucket of LATENCY_BUCKETS) {
    if (latencyMs <= bucket) {
      return bucket;
    }
  }
  return LATENCY_BUCKETS[LATENCY_BUCKETS.length - 1];
}
var ClearcutLogger = class {
  #watchdog = null;
  #skillVersion;
  #agent;
  constructor(options = {}) {
    if (!isTelemetryEnabled()) {
      return;
    }
    this.#skillVersion = options.skillVersion ?? void 0;
    this.#agent = options.agent ?? determineAgent().agent?.name;
    this.#watchdog = new WatchdogClient({
      clearcutEndpoint: options.clearcutEndpoint,
      clearcutIncludePidHeader: options.clearcutIncludePidHeader
    });
  }
  async logSearchResult(query, latencyMs, success, searchItems) {
    if (!this.#watchdog) {
      return;
    }
    const payload = {
      search_result: {
        query,
        search_items: searchItems
      },
      os: detectOS(),
      version: getVersion(import.meta.dirname),
      skill_version: this.#skillVersion,
      agent: this.#agent,
      latency_ms: bucketizeLatency(latencyMs),
      success
    };
    this.#watchdog.send({
      type: WatchdogMessageType.LOG_EVENT,
      payload
    });
  }
  async logRetrieveResult(latencyMs, success, guideId) {
    if (!this.#watchdog) {
      return;
    }
    const payload = {
      retrieve_result: {
        guide_id: guideId
      },
      os: detectOS(),
      version: getVersion(import.meta.dirname),
      skill_version: this.#skillVersion,
      agent: this.#agent,
      latency_ms: bucketizeLatency(latencyMs),
      success
    };
    this.#watchdog.send({
      type: WatchdogMessageType.LOG_EVENT,
      payload
    });
  }
  async logToolCommand(latencyMs, success, commandType) {
    if (!this.#watchdog) {
      return;
    }
    if (commandType == CommandType.INSTALL || commandType == CommandType.INSTALL_CHOOSE) {
      console.warn(
        "Google collects anonymous usage information to improve the reliability, relevance, and performance of the Modern Web Guidance tool. You can opt-out completely at any time by setting the DISABLE_TELEMETRY=1 environment variable in your shell profile. See https://github.com/GoogleChrome/modern-web-guidance#-telemetry--privacy for more details."
      );
    }
    const payload = {
      tool_command: {
        command_type: commandType
      },
      os: detectOS(),
      version: getVersion(import.meta.dirname),
      skill_version: this.#skillVersion,
      agent: this.#agent,
      latency_ms: bucketizeLatency(latencyMs),
      success
    };
    this.#watchdog.send({
      type: WatchdogMessageType.LOG_EVENT,
      payload
    });
  }
};

// src/cli/skill-version.ts
var MS_PER_DAY = 1e3 * 60 * 60 * 24;
function parseVersionDate(version) {
  const match = version?.match(/^(\d{4})_(\d{2})_(\d{2})/);
  if (!match) return null;
  const [_, year, month, day] = match;
  return new Date(parseInt(year, 10), parseInt(month, 10) - 1, parseInt(day, 10));
}
function getSkillUpdateLevel(callerVersion, latestVersion, now = Date.now()) {
  const callerDate = parseVersionDate(callerVersion);
  const latestDate = parseVersionDate(latestVersion);
  if (!callerDate || !latestDate || callerDate >= latestDate) return "none";
  const diffDays = Math.floor((now - callerDate.getTime()) / MS_PER_DAY);
  if (diffDays <= 5) return "none";
  return diffDays >= 60 ? "insist" : "warn";
}

// src/cli/modern-web.ts
var MAX_INLINE_STDOUT_BYTES = 9500;
var { values, positionals } = parseArgs({
  args: process.argv.slice(2),
  options: {
    help: { type: "boolean", short: "h" },
    version: { type: "boolean", short: "v" },
    choose: { type: "boolean" },
    "skill-version": { type: "string" }
  },
  allowPositionals: true,
  strict: false
});
function isStdoutRedirectedToFile() {
  try {
    return fstatSync(1).isFile();
  } catch {
    return false;
  }
}
function saveRetrievedGuides(content) {
  const filename = `mwg-guide-${process.pid}-${Date.now()}.md`;
  const candidateDirs = [.../* @__PURE__ */ new Set([tmpdir(), "/tmp"])];
  for (const dir of candidateDirs) {
    try {
      if (!existsSync3(dir)) continue;
      const filePath = join2(dir, filename);
      writeFileSync(filePath, content, "utf8");
      return filePath;
    } catch {
    }
  }
  return null;
}
function printUsage() {
  console.log(`
Usage: modern-web <command> [args]

Commands:
  search <query>            Search use cases by query
  list                      List all available use cases
  retrieve <ids>            Retrieve use case(s) by ID(s), comma-separated
  set-allow-origin-trials   Opt in to experimental Origin Trial guidance
  install [options]         Install the modern-web-guidance skill
  uninstall                 Uninstall the modern-web-guidance skill
  update                    Update skills

Options:
  --skill-version <version> Internal use: version of the skill being executed
  --choose                  Choose specific skills from the repository interactively
  -h, --help                Show this help
  -v, --version             Show version
`);
}
async function main() {
  if (values.version) {
    console.log(getVersion(import.meta.dirname));
    process.exit(0);
  }
  if (values.help || positionals.length === 0) {
    printUsage();
    process.exit(values.help ? 0 : 1);
  }
  const skillVersion = typeof values["skill-version"] === "string" ? values["skill-version"] : null;
  maybeEmitUpdateMessage(skillVersion);
  let loggerInstance;
  const getLogger = () => loggerInstance ??= new ClearcutLogger({ skillVersion });
  const command = positionals[0];
  const arg = positionals.slice(1).join(" ");
  if (command === "search") {
    if (!arg) {
      await getLogger().logSearchResult("", 0, false, []);
      console.error("No search query provided.");
      process.exit(1);
    }
    const startTime = Date.now();
    try {
      const { searchUseCases } = await import("./search.mjs");
      const results = await searchUseCases(arg);
      const latencyMs = Date.now() - startTime;
      const searchItems = results.map((r) => ({
        guide_id: r.id,
        similarity: Number(r.similarity)
      }));
      await getLogger().logSearchResult(arg, latencyMs, true, searchItems);
      const jsonLines = results.map(({ id, description }) => JSON.stringify({ id, description }));
      console.log("[" + jsonLines.join(",\n") + "]");
    } catch (error) {
      const latencyMs = Date.now() - startTime;
      await getLogger().logSearchResult(arg, latencyMs, false, []);
      console.error("Search failed:", error);
      process.exit(1);
    }
  } else if (command === "list") {
    const startTime = Date.now();
    try {
      const jsonLines = USE_CASES.map(({ id, description }) => JSON.stringify({ id, description }));
      console.log("[" + jsonLines.join(",\n") + "]");
      await getLogger().logToolCommand(Date.now() - startTime, true, CommandType.LIST);
    } catch (error) {
      await getLogger().logToolCommand(Date.now() - startTime, false, CommandType.LIST);
      console.error("List failed:", error);
      process.exit(1);
    }
  } else if (command === "retrieve") {
    const ids = arg ? [
      ...new Set(
        arg.split(/[\s,;]+/).map((id) => id.replace(/^["'\\]+|["'\\;]+$/g, "").trim()).filter((id) => Boolean(id) && !id.startsWith("-"))
      )
    ] : [];
    if (ids.length === 0) {
      await getLogger().logRetrieveResult(0, false, "");
      console.error("No IDs provided for retrieve.");
      process.exit(1);
    }
    let hasError = false;
    const retrievedSections = [];
    for (const id of ids) {
      const startTime = Date.now();
      try {
        const guide = await retrieveUseCase(id);
        retrievedSections.push(`
--- Guide for ${id} ---
${guide}`);
        await getLogger().logRetrieveResult(Date.now() - startTime, true, id);
      } catch (error) {
        hasError = true;
        if (error instanceof OriginTrialGateError) {
          console.error(error.message);
        } else {
          console.error(`Retrieve failed for ${id}:`, error);
        }
        await getLogger().logRetrieveResult(Date.now() - startTime, false, id);
      }
    }
    if (retrievedSections.length > 0) {
      const combinedStdout = retrievedSections.join("\n");
      const totalBytes = Buffer.byteLength(combinedStdout, "utf8");
      const shouldSaveToFile = totalBytes > MAX_INLINE_STDOUT_BYTES && !isStdoutRedirectedToFile();
      if (shouldSaveToFile) {
        const fileContent = combinedStdout.replace(/^\n+/, "") + "\n";
        const savedPath = saveRetrievedGuides(fileContent);
        if (savedPath) {
          const lineCount = fileContent.split("\n").length - 1;
          const sizeKb = (totalBytes / 1024).toFixed(1);
          console.log(
            `Output (${sizeKb} KB, ${lineCount} lines) saved to ${savedPath} to prevent CLI stdout truncation.
Read ${savedPath} in full using your file-reading tool (${lineCount} lines total)\u2014do not use cat or head.`
          );
        } else {
          console.log(combinedStdout);
        }
      } else {
        console.log(combinedStdout);
      }
    }
    if (hasError) {
      process.exit(1);
    }
  } else if (command === "install") {
    const startTime = Date.now();
    const extraArgs = process.argv.slice(3).filter((a) => a !== "--choose");
    const installArgs = `-y skills add GoogleChrome/modern-web-guidance ${values.choose ? "" : "--skill modern-web-guidance"}`.split(" ").filter(Boolean).concat(extraArgs);
    const detectedAgent = determineAgent().agent?.name;
    const env = detectedAgent ? { ...process.env, AI_AGENT: detectedAgent } : process.env;
    const result = spawnSync("npx", installArgs, {
      stdio: "inherit",
      shell: process.platform === "win32",
      env
    });
    const success = !result.error && result.status === 0;
    const commandType = values.choose ? CommandType.INSTALL_CHOOSE : CommandType.INSTALL;
    await getLogger().logToolCommand(Date.now() - startTime, success, commandType);
    if (result.error) {
      console.error("Install failed:", result.error);
      process.exit(1);
    }
    process.exit(result.status ?? 0);
  } else if (command === "update") {
    const startTime = Date.now();
    const skills = getOurCLIAdjacentSkillIDs();
    const result = spawnSync("npx", ["-y", "skills", "update", ...skills], {
      stdio: "inherit",
      shell: process.platform === "win32"
    });
    const success = !result.error && result.status === 0;
    await getLogger().logToolCommand(Date.now() - startTime, success, CommandType.UPDATE);
    if (result.error) {
      console.error("Update failed:", result.error);
    }
  } else if (command === "set-allow-origin-trials") {
    const code = await handleSetAllowOriginTrials();
    process.exit(code);
  } else if (command === "uninstall") {
    const startTime = Date.now();
    const skills = getOurCLIAdjacentSkillIDs();
    const result = spawnSync("npx", ["skills", "remove", ...skills], {
      stdio: "inherit",
      shell: process.platform === "win32"
    });
    const success = !result.error && result.status === 0;
    await getLogger().logToolCommand(Date.now() - startTime, success, CommandType.UNINSTALL);
    if (result.error) {
      console.error("Uninstall failed:", result.error);
    }
  } else {
    console.error(`Unknown command: ${command}`);
    printUsage();
    process.exit(1);
  }
}
function getCLISkillVersion() {
  try {
    const versionPath = join2(import.meta.dirname, "skill-version.txt");
    const version = readFileSync3(versionPath, "utf8");
    return version.trim();
  } catch (e) {
    return null;
  }
}
function getOurCLIAdjacentSkillIDs() {
  try {
    const parentDir = dirname2(import.meta.dirname);
    const skillsPath = basename(parentDir) === "skills" ? parentDir : join2(dirname2(parentDir), "skills");
    const listing = readdirSync(skillsPath);
    return listing.filter((name) => existsSync3(join2(skillsPath, name, "SKILL.md")));
  } catch (e) {
    return [];
  }
}
function maybeEmitUpdateMessage(callerSkillVersion) {
  const latestSkillVersion = getCLISkillVersion();
  const level = getSkillUpdateLevel(callerSkillVersion, latestSkillVersion);
  if (level === "none") {
    return;
  }
  if (level === "insist") {
    console.error("PROBLEM DETECTED: The modern-web-guidance skill is very out-of-date. It requires an update to ensure top-quality performance. Without an update, the user may be disappointed in the results. Be a great agent and insist that the user upgrade the skill.");
  }
  const skillName = "modern-web-guidance";
  console.error([
    `Warning: a new SKILL.md is available for ${skillName}. Please update.`,
    "",
    `Your version: ${callerSkillVersion}`,
    `Latest version: ${latestSkillVersion}`,
    "",
    "See the docs for how to update: https://github.com/GoogleChrome/modern-web-guidance#updating"
  ].join("\n"));
}
main().catch((err) => {
  console.error("Execution failed:", err);
  process.exit(1);
});
/**
 * @license
 * Copyright 2025 Vercel, Inc.
 * Copyright 2026 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 *
 * Vendored and adapted from @vercel/detect-agent@1.2.5
 * Upstream: https://github.com/vercel/vercel/tree/main/packages/detect-agent
 *
 * Checks environment variables and known runtime indicators to detect what AI
 * agent or automated development environment is executing the CLI.
 */
/**
 * @license
 * Copyright 2026 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */
