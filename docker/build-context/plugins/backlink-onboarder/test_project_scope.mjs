#!/usr/bin/env node
import assert from "node:assert/strict";
import {
  GROUP_SESSION_KEY_RE,
  parseGroupIdFromSessionKey,
  buildProjectScopeContext,
} from "./project_scope.mjs";

assert.match(
  "agent:bl-orchestrator:telegram:group:-1004320744048",
  GROUP_SESSION_KEY_RE,
);
assert.equal(
  parseGroupIdFromSessionKey("agent:bl-orchestrator:telegram:group:-1004320744048"),
  "-1004320744048",
);
assert.equal(
  parseGroupIdFromSessionKey("agent:bl-orchestrator:telegram:group:-1004425478738"),
  "-1004425478738",
);
assert.equal(parseGroupIdFromSessionKey("agent:bl-orchestrator:main"), null);
assert.equal(parseGroupIdFromSessionKey(""), null);

const ctx = buildProjectScopeContext("https://coinography.com");
assert.ok(ctx.includes("PROJECT_URL=https://coinography.com"));
assert.ok(ctx.includes("EXCLUSIVELY"));

console.log("OK: project_scope sessionKey parsing validated");
