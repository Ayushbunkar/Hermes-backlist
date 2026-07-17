import { spawnSync } from "node:child_process";
import os from "node:os";
import path from "node:path";

const DB_PATH = path.join(os.homedir(), ".openclaw-backlink", "data/backlink.db");

/** Matches agent:bl-orchestrator:telegram:group:-1004320744048 */
export const GROUP_SESSION_KEY_RE = /:group:(-?\d+)$/;

/**
 * @param {string | undefined | null} sessionKey
 * @returns {string | null}
 */
export function parseGroupIdFromSessionKey(sessionKey) {
  if (!sessionKey) return null;
  const m = String(sessionKey).match(GROUP_SESSION_KEY_RE);
  return m ? m[1] : null;
}

/**
 * @param {string} chatId
 * @returns {string | null}
 */
export function resolveProjectForGroup(chatId) {
  const gid = String(chatId ?? "").trim();
  if (!/^-?\d+$/.test(gid)) return null;
  try {
    const sql =
      "SELECT project_url FROM projects WHERE telegram_group_id IS NOT NULL " +
      `AND trim(telegram_group_id) = trim('${gid.replace(/'/g, "''")}') LIMIT 1;`;
    const result = spawnSync("sqlite3", [DB_PATH, sql], {
      encoding: "utf8",
      timeout: 5000,
    });
    if (result.status === 0) {
      const url = (result.stdout || "").trim();
      if (url) return url;
    }
  } catch {
    // Fail open — no project scope injected.
  }
  return null;
}

/**
 * @param {string} projectUrl
 * @returns {string}
 */
export function buildProjectScopeContext(projectUrl) {
  return (
    `PROJECT_URL=${projectUrl}. You operate EXCLUSIVELY for this project in this group. ` +
    "Never ask which project; never act on other projects here."
  );
}

/**
 * @param {Record<string, unknown>} ctx
 * @param {{ info?: (msg: string) => void; warn?: (msg: string) => void }} logger
 * @returns {{ appendSystemContext: string } | undefined}
 */
export function resolveDynamicProjectScope(ctx, logger) {
  const chatId = parseGroupIdFromSessionKey(
    typeof ctx.sessionKey === "string" ? ctx.sessionKey : "",
  );
  if (!chatId) return undefined;

  const projectUrl = resolveProjectForGroup(chatId);
  if (!projectUrl) {
    logger.info?.(`backlink-onboarder: no DB project for group ${chatId} (fail-open)`);
    return undefined;
  }

  logger.info?.(`backlink-onboarder: dynamic scope ${projectUrl} for group ${chatId}`);
  return { appendSystemContext: buildProjectScopeContext(projectUrl) };
}
