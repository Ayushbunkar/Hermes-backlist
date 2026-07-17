import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { resolveDynamicProjectScope } from "./project_scope.mjs";

const OPENCLAW_HOME = path.join(os.homedir(), ".openclaw-backlink");
const ENGINE_SCRIPT = path.join(
  OPENCLAW_HOME,
  "workspace-bl-orchestrator/skills/pipeline/onboard_backlink.py",
);
const DB_PATH = path.join(OPENCLAW_HOME, "data/backlink.db");
const TELEGRAM_ACCOUNT_ID = "backlink";
const ONBOARD_MENU_ENTRY = { command: "onboard", description: "Add backlink project" };
const MENU_RECOVERY_DELAY_MS = 15_000;

const CALLBACK_PREFIXES = ["ob_confirm:"];

let menuRecoveryTimer = null;

/**
 * @param {string} chatId
 * @param {string} userId
 * @returns {string | null}
 */
function getOnboardSessionStep(chatId, userId) {
  if (!/^-?\d+$/.test(chatId) || !/^\d+$/.test(userId)) return null;
  try {
    const sql = `SELECT step FROM onboard_sessions WHERE chat_id='${chatId}' AND user_id='${userId}' LIMIT 1;`;
    const result = spawnSync("sqlite3", [DB_PATH, sql], {
      encoding: "utf8",
      timeout: 5000,
    });
    if (result.status === 0) {
      const step = result.stdout.trim();
      if (step) return step;
    }
  } catch {
    // Fail open — step lookup unavailable.
  }
  return null;
}

/**
 * @param {Record<string, unknown>} event
 * @returns {string | null}
 */
function extractText(event) {
  const fields = [event.content, event.body, event.bodyForAgent];
  for (const field of fields) {
    if (typeof field === "string" && field.trim()) return field.trim();
  }
  return null;
}

function baseChatId(conversationId) {
  const raw = String(conversationId ?? "").trim();
  const topicIdx = raw.indexOf(":topic:");
  return topicIdx >= 0 ? raw.slice(0, topicIdx) : raw;
}

/**
 * @param {string | undefined} from
 * @param {string | undefined} to
 * @returns {string}
 */
function parseTelegramChatId(from, to) {
  for (const raw of [to, from]) {
    if (!raw) continue;
    const s = String(raw).trim();
    const tailMatch = s.match(/(-100\d+|-\d+)$/);
    if (tailMatch) return tailMatch[1];
    if (s.startsWith("telegram:")) {
      const id = s.slice("telegram:".length).split(":").pop() ?? "";
      if (/^-?\d+$/.test(id)) return id;
    }
  }
  return "";
}

/**
 * @param {Record<string, unknown>} event
 * @param {Record<string, unknown>} ctx
 * @returns {boolean}
 */
function isTelegramGroupMessage(event, ctx) {
  if (ctx.channelId && ctx.channelId !== "telegram") return false;
  if (event.channel && event.channel !== "telegram") return false;
  if (event.isGroup === false) return false;
  return true;
}

function runEngine(args) {
  const result = spawnSync("python3", [ENGINE_SCRIPT, ...args], {
    encoding: "utf8",
    timeout: 120_000,
    env: process.env,
  });
  if (result.error) {
    return { ok: false, detail: String(result.error) };
  }
  if (result.status !== 0) {
    const stderr = (result.stderr || "").trim();
    const stdout = (result.stdout || "").trim();
    return { ok: false, detail: stderr || stdout || `exit ${result.status ?? "unknown"}` };
  }
  return { ok: true, detail: (result.stdout || "").trim() };
}

/**
 * @param {import("openclaw/plugin-sdk/plugins/types").PluginCommandContext} ctx
 * @param {{ warn?: (msg: string) => void; info?: (msg: string) => void }} logger
 * @param {"start" | "cancel"} subcommand
 */
function runOnboardCommand(ctx, logger, subcommand) {
  if (!fs.existsSync(ENGINE_SCRIPT)) {
    logger.warn?.(`backlink-onboarder: engine missing at ${ENGINE_SCRIPT}`);
    return { text: "Onboarding engine is not installed." };
  }

  const chatId = parseTelegramChatId(ctx.from, ctx.to);
  const userId = String(ctx.senderId ?? "");
  if (!chatId || !userId) {
    return { text: "Could not resolve chat/user for onboarding." };
  }

  const outcome = runEngine([subcommand, "--chat-id", chatId, "--user-id", userId]);
  if (!outcome.ok) {
    logger.warn?.(`backlink-onboarder: ${subcommand} failed: ${outcome.detail}`);
    return { text: `Onboarding failed: ${outcome.detail}` };
  }

  logger.info?.(`backlink-onboarder: ${subcommand} via registerCommand for ${chatId}`);
  return {};
}

/**
 * @param {Record<string, unknown>} cfg
 * @returns {string | null}
 */
function loadBacklinkBotToken(cfg) {
  const token = cfg?.channels?.telegram?.accounts?.[TELEGRAM_ACCOUNT_ID]?.botToken;
  return typeof token === "string" && token.trim() ? token.trim() : null;
}

/**
 * @param {string} token
 * @param {string} method
 * @param {Record<string, unknown>} body
 */
async function telegramBotApi(token, method, body) {
  const url = `https://api.telegram.org/bot${token}/${method}`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return resp.json();
}

/**
 * @param {Record<string, unknown>} cfg
 * @param {{ warn?: (msg: string) => void; info?: (msg: string) => void }} logger
 */
async function ensureOnboardInTelegramMenu(cfg, logger) {
  const token = loadBacklinkBotToken(cfg);
  if (!token) {
    logger.warn?.("backlink-onboarder: no backlink bot token; skipping menu recovery");
    return;
  }

  const getResp = await telegramBotApi(token, "getMyCommands", {});
  if (!getResp?.ok) {
    logger.warn?.(
      `backlink-onboarder: getMyCommands failed: ${getResp?.description ?? "unknown error"}`,
    );
    return;
  }

  /** @type {Array<{ command: string; description: string }>} */
  const existing = Array.isArray(getResp.result) ? getResp.result : [];
  if (existing.some((entry) => entry.command === "onboard")) {
    logger.info?.("backlink-onboarder: /onboard already present in Telegram menu");
    return;
  }

  let merged = [ONBOARD_MENU_ENTRY, ...existing.filter((entry) => entry.command !== "onboard")];
  while (merged.length > 0) {
    const setResp = await telegramBotApi(token, "setMyCommands", { commands: merged });
    if (setResp?.ok) {
      logger.info?.(
        `backlink-onboarder: prepended /onboard to Telegram menu (${merged.length} commands)`,
      );
      return;
    }
    const desc = String(setResp?.description ?? "");
    if (setResp?.error_code === 400 && /BOT_COMMANDS_TOO_MUCH/i.test(desc)) {
      merged = merged.slice(0, -1);
      continue;
    }
    logger.warn?.(`backlink-onboarder: setMyCommands failed: ${desc || "unknown error"}`);
    return;
  }
  logger.warn?.("backlink-onboarder: could not fit /onboard into Telegram menu");
}

/**
 * @param {Record<string, unknown>} event
 * @param {Record<string, unknown>} ctx
 * @param {{ info?: (msg: string) => void; warn?: (msg: string) => void }} logger
 * @returns {{ handled: boolean }}
 */
function handleOnboardEvent(event, ctx, logger) {
  try {
    if (!isTelegramGroupMessage(event, ctx)) return { handled: false };

    const text = extractText(event);
    if (!text) return { handled: false };

    const chatId = baseChatId(
      typeof ctx.conversationId === "string"
        ? ctx.conversationId
        : typeof event.conversationId === "string"
          ? event.conversationId
          : "",
    );
    const senderId =
      (typeof ctx.senderId === "string" && ctx.senderId) ||
      (typeof event.senderId === "string" && event.senderId) ||
      "";
    if (!chatId || !senderId) return { handled: false };

    // Only intercept when THIS sender has an active wizard session (never chat-wide).
    const sessionStep = getOnboardSessionStep(chatId, senderId);
    if (!sessionStep) return { handled: false };

    // Slash commands use registerCommand (/onboard, /cancel), not step.
    if (text.startsWith("/")) return { handled: false };

    const isCallback = CALLBACK_PREFIXES.some((p) => text.startsWith(p));
    if (isCallback && sessionStep !== "preview") return { handled: false };

    if (!fs.existsSync(ENGINE_SCRIPT)) {
      logger.warn?.(`backlink-onboarder: engine missing at ${ENGINE_SCRIPT}; falling through`);
      return { handled: false };
    }

    const messageId =
      (typeof ctx.messageId === "string" && ctx.messageId) ||
      (typeof event.messageId === "string" && event.messageId) ||
      "";

    /** @type {string[]} */
    const args = ["step", "--chat-id", chatId, "--user-id", String(senderId), "--input", text];
    if (messageId) args.push("--reply-to-message-id", messageId);
    const outcome = runEngine(args);

    if (!outcome.ok) {
      logger.warn?.(`backlink-onboarder: engine failed: ${outcome.detail}`);
      return { handled: false };
    }

    if (outcome.detail.includes("ERROR: no active session")) {
      return { handled: false };
    }

    logger.info?.(`backlink-onboarder: handled step for ${chatId}`);
    return { handled: true };
  } catch (err) {
    logger.warn?.(`backlink-onboarder: unexpected error: ${String(err)}`);
    return { handled: false };
  }
}

export default definePluginEntry({
  id: "backlink-onboarder",
  name: "Backlink Onboarder",
  description:
    "Deterministic /onboard flow and DB-driven per-group project scoping for LinkNexus (no openclaw.json per-project wiring).",
  register(api) {
    const logger = api.logger;

    api.on(
      "before_prompt_build",
      async (_event, ctx) => resolveDynamicProjectScope(ctx, logger),
      { priority: 100 },
    );

    api.on(
      "before_agent_start",
      async (_event, ctx) => resolveDynamicProjectScope(ctx, logger),
      { priority: 100 },
    );

    api.registerCommand({
      name: "onboard",
      description: "Add a new backlink project (Telegram group + whitelist seed)",
      requireAuth: false,
      handler: async (ctx) => runOnboardCommand(ctx, logger, "start"),
    });

    api.registerCommand({
      name: "cancel",
      description: "Cancel an in-progress backlink onboarding session",
      requireAuth: false,
      handler: async (ctx) => runOnboardCommand(ctx, logger, "cancel"),
    });

    api.registerService({
      id: "backlink-onboard-menu-recovery",
      start: (ctx) => {
        if (menuRecoveryTimer) clearTimeout(menuRecoveryTimer);
        menuRecoveryTimer = setTimeout(() => {
          ensureOnboardInTelegramMenu(ctx.config, logger).catch((err) => {
            logger.warn?.(`backlink-onboarder: menu recovery error: ${String(err)}`);
          });
        }, MENU_RECOVERY_DELAY_MS);
      },
      stop: () => {
        if (menuRecoveryTimer) {
          clearTimeout(menuRecoveryTimer);
          menuRecoveryTimer = null;
        }
      },
    });

    api.on(
      "before_dispatch",
      async (event, ctx) => handleOnboardEvent(event, ctx, logger),
      { priority: 90 },
    );

    api.on(
      "inbound_claim",
      async (event, ctx) => handleOnboardEvent(event, ctx, logger),
      { priority: 90 },
    );
  },
});
