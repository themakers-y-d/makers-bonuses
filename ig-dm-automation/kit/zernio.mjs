#!/usr/bin/env node
// zernio.mjs - comment-to-DM control plane on top of Zernio.
//
// A gift from MAKERS. It is yours: change it, break it, rewrite it. themakers.co.il
//
// Hard rules baked in:
//   - the API key is read from ~/.config/ig-dm/zernio.env (local disk, never a synced
//     folder like iCloud or Dropbox, never this repo). A scheduled run is blocked from
//     synced and external drives and fails silently, which looks exactly like a code bug.
//   - the key is never printed, never logged, never echoed back in errors.
//   - every subcommand prints what it is about to do BEFORE it does it.
//   - writes are dry-run by default. --apply is required to touch the live account.
//   - placeholders in automations.json abort any real call.

import { readFileSync, existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const BASE = process.env.ZERNIO_BASE_URL || 'https://zernio.com/api/v1';
const ENV_FILE = join(homedir(), '.config', 'ig-dm', 'zernio.env');
const CONFIG_FILE = join(HERE, 'automations.json');
const PLACEHOLDER = /^(REPLACE_ME|TODO|CHANGEME)/i;

const argv = process.argv.slice(2);
const cmd = argv[0];
const flags = new Set(argv.filter((a) => a.startsWith('--')));
const positional = argv.slice(1).filter((a) => !a.startsWith('--'));
const APPLY = flags.has('--apply');

function die(msg, code = 1) {
  console.error(`\nzernio: ${msg}\n`);
  process.exit(code);
}

function loadKey() {
  if (process.env.ZERNIO_API_KEY) return process.env.ZERNIO_API_KEY.trim();
  if (!existsSync(ENV_FILE)) {
    die(
      `no API key.\n` +
        `  expected ${ENV_FILE} with a line: ZERNIO_API_KEY=sk_...\n` +
        `  create the key at https://zernio.com/dashboard (API keys), it is shown once.`
    );
  }
  const line = readFileSync(ENV_FILE, 'utf8')
    .split('\n')
    .map((l) => l.trim())
    .find((l) => l.startsWith('ZERNIO_API_KEY='));
  if (!line) die(`${ENV_FILE} exists but has no ZERNIO_API_KEY= line.`);
  const key = line.slice('ZERNIO_API_KEY='.length).trim().replace(/^["']|["']$/g, '');
  if (!key) die(`ZERNIO_API_KEY in ${ENV_FILE} is empty.`);
  if (PLACEHOLDER.test(key)) die(`ZERNIO_API_KEY is still a placeholder. Paste the real key.`);
  if (!/^sk_[0-9a-f]{64}$/.test(key)) {
    console.error(`zernio: warning - key does not look like sk_ + 64 hex. Sending it anyway.`);
  }
  return key;
}

async function api(method, path, body) {
  const key = loadKey();
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    method,
    headers: {
      Authorization: `Bearer ${key}`,
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json;
  try {
    json = text ? JSON.parse(text) : {};
  } catch {
    json = { raw: text };
  }
  if (!res.ok) {
    // never echo the key; the URL and body are safe to show.
    const detail = typeof json === 'object' ? JSON.stringify(json).slice(0, 800) : String(text).slice(0, 800);
    die(`${method} ${path} -> HTTP ${res.status}\n  ${detail}`);
  }
  return json;
}

function loadConfig() {
  if (!existsSync(CONFIG_FILE)) die(`missing ${CONFIG_FILE}`);
  const cfg = JSON.parse(readFileSync(CONFIG_FILE, 'utf8'));
  const blob = JSON.stringify(cfg);
  const hit = blob.match(/(REPLACE_ME[A-Z_]*)/);
  if (hit) {
    die(
      `automations.json still contains the placeholder ${hit[1]}.\n` +
        `  fill it in before any real call. Nothing was sent.`
    );
  }
  return cfg;
}

// ---- account resolution -------------------------------------------------

async function resolveAccount(cfg) {
  const { accounts } = await api('GET', '/accounts');
  const list = accounts || [];
  const want = (cfg.accountUsername || '').toLowerCase();
  const igs = list.filter((a) => a.platform === 'instagram');
  const match = want ? igs.find((a) => (a.username || '').toLowerCase() === want) : igs[0];
  if (!match) {
    die(
      `no connected Instagram account matching "${cfg.accountUsername}".\n` +
        `  connected: ${list.map((a) => `${a.platform}:${a.username}`).join(', ') || '(none)'}\n` +
        `  connect it at https://zernio.com/dashboard first.`
    );
  }
  if (!match.isActive) die(`account ${match.username} is connected but not active in Zernio.`);
  return match;
}

function accountIdOf(a) {
  return a._id || a.id;
}

// guard: a payload id must always be a string, never a populated object.
function assertIdString(label, v) {
  if (typeof v !== 'string' || !v) die(`${label} resolved to ${JSON.stringify(v)}, expected an id string. Nothing was sent.`);
  return v;
}

// Zernio returns profileId either as a plain id string or as a populated {_id, name}
// object, depending on the endpoint. Always reduce it to the id string: sending the
// object produces "[object Object]" in the payload and a useless 4xx.
function idOf(v) {
  if (!v) return null;
  if (typeof v === 'string') return v;
  return v._id || v.id || null;
}

async function resolveProfileId(account, cfg) {
  const fromCfg = idOf(cfg.profileId);
  if (fromCfg && !PLACEHOLDER.test(fromCfg)) return fromCfg;
  const fromAccount = idOf(account.profileId);
  if (fromAccount) return fromAccount;
  try {
    const p = await api('GET', '/profiles');
    const first = (p.profiles || p.data || [])[0];
    if (first) return idOf(first);
  } catch {
    /* endpoint may not exist; fall through */
  }
  die(
    `could not resolve profileId.\n` +
      `  run "node zernio.mjs accounts" and copy the profile id into automations.json.`
  );
}

// ---- payload construction -----------------------------------------------

function buildPayload(rule, ctx) {
  const p = {
    profileId: assertIdString('profileId', ctx.profileId),
    accountId: assertIdString('accountId', ctx.accountId),
    name: rule.name,
    trigger: rule.trigger || 'comment',
    keywords: rule.keywords,
    matchMode: rule.matchMode || 'contains',
    dmMessage: rule.dmMessage,
  };
  if (rule.excludeKeywords?.length) p.excludeKeywords = rule.excludeKeywords;
  if (rule.dmMessageVariations?.length) p.dmMessageVariations = rule.dmMessageVariations;
  if (rule.commentReply) p.commentReply = rule.commentReply;
  if (rule.commentReplyVariations?.length) p.commentReplyVariations = rule.commentReplyVariations;
  if (rule.buttons?.length) p.buttons = rule.buttons;
  // Always send this one, including as null. Omitting it on a PATCH leaves an
  // existing post scope in place, so "make this rule account-wide" would report
  // success and change nothing. Found the hard way on 2026-09-20.
  p.platformPostId = rule.platformPostId ?? null;
  if (rule.audience) p.audience = rule.audience;
  if (rule.followGate) p.followGate = rule.followGate;
  if (typeof rule.alsoMatchInDms === 'boolean') p.alsoMatchInDms = rule.alsoMatchInDms;
  if (typeof rule.dmDelaySeconds === 'number') p.dmDelaySeconds = rule.dmDelaySeconds;
  if (typeof rule.commentReplyDelaySeconds === 'number') p.commentReplyDelaySeconds = rule.commentReplyDelaySeconds;
  if (typeof rule.linkTracking === 'boolean') p.linkTracking = rule.linkTracking;
  if (rule.clickTag) p.clickTag = rule.clickTag;
  return p;
}

// ---- the audit (Romi's condition, and the guide's third safety layer) ----

const SHORT_KEYWORD_FLOOR = 4; // Hebrew prefixes glue onto words; anything shorter is a net.

export function audit(cfg) {
  const problems = [];
  const warnings = [];
  const seen = new Map();

  for (const r of cfg.automations) {
    const label = r.name;
    if (!r.keywords?.length) problems.push(`${label}: no keywords`);
    if (!r.dmMessage) problems.push(`${label}: no dmMessage`);

    for (const k of r.keywords || []) {
      if (k.length < SHORT_KEYWORD_FLOOR && (r.matchMode || 'contains') === 'contains') {
        problems.push(`${label}: keyword "${k}" is ${k.length} chars on matchMode=contains. Too short, it will catch unrelated comments.`);
      }
      if (/\s/.test(k)) {
        warnings.push(`${label}: keyword "${k}" contains a space. Matching across a space is unreliable.`);
      }
      const key = `${k.toLowerCase()}|${r.trigger || 'comment'}|${r.platformPostId || '*'}`;
      if (seen.has(key)) problems.push(`${label}: keyword "${k}" collides with "${seen.get(key)}" on the same scope. One of them will never fire.`);
      else seen.set(key, label);
    }

    const msgs = [r.dmMessage, ...(r.dmMessageVariations || [])].filter(Boolean);
    for (const m of msgs) {
      const cap = r.buttons?.length ? 640 : 1000;
      if (m.length > cap) problems.push(`${label}: a DM variant is ${m.length} chars, over the ${cap} cap for this shape.`);
      if (/\b(bit\.ly|tinyurl|t\.co|short\.link|cutt\.ly)\b/i.test(m)) {
        problems.push(`${label}: shortened link in the DM. Meta treats shorteners in DMs as a spam signal.`);
      }
    }

    if (!r.platformPostId && (r.trigger || 'comment') === 'comment') {
      warnings.push(`${label}: account-wide rule (no platformPostId). Anyone commenting this word on ANY old post gets the DM.`);
    }
    if (r.audience?.followerStatus === 'follower' && !r.followGate) {
      problems.push(`${label}: follower-only audience without followGate copy. Non-followers get dropped silently.`);
    }
    if (r.followGate && r.audience?.whenUnknown !== 'verify') {
      warnings.push(`${label}: followGate copy is set but whenUnknown is not "verify", so the gate may never render.`);
    }
  }
  return { problems, warnings };
}

// ---- commands -----------------------------------------------------------

function printAutomation(a, i) {
  const scope = a.platformPostId ? `post ${a.platformPostId}` : 'ACCOUNT-WIDE';
  const st = a.stats || {};
  console.log(
    `  ${String(i + 1).padStart(2)}. ${a.name}\n` +
      `      id=${a.id}  trigger=${a.trigger}  match=${a.matchMode}  active=${a.isActive}\n` +
      `      keywords: ${(a.keywords || []).join(', ')}\n` +
      `      scope: ${scope}\n` +
      `      stats: triggered=${st.triggered ?? '-'} sent=${st.dmsSent ?? '-'} delivered=${st.delivered ?? '-'} clicks=${st.linkClicks ?? '-'}`
  );
}

const commands = {
  async doctor() {
    console.log(`about to: read the key from ${ENV_FILE} and call GET /accounts (read only).`);
    const { accounts } = await api('GET', '/accounts');
    const list = accounts || [];
    console.log(`\nkey: present and accepted by Zernio.`);
    console.log(`connected accounts: ${list.length}`);
    for (const a of list) {
      console.log(`  ${a.platform.padEnd(10)} ${a.username}  active=${a.isActive}  id=${accountIdOf(a)}`);
    }
    const cfg = loadConfig();
    const { problems, warnings } = audit(cfg);
    console.log(`\nconfig audit: ${problems.length} blocking, ${warnings.length} warning`);
    for (const p of problems) console.log(`  BLOCK  ${p}`);
    for (const w of warnings) console.log(`  warn   ${w}`);
    if (problems.length) process.exit(2);
  },

  async accounts() {
    console.log('about to: GET /accounts (read only).');
    const out = await api('GET', '/accounts');
    console.log(JSON.stringify(out, null, 2));
  },

  async list() {
    console.log('about to: GET /comment-automations (read only).');
    const out = await api('GET', '/comment-automations');
    const items = out.automations || [];
    console.log(`\n${items.length} automation(s) live:\n`);
    items.forEach(printAutomation);
  },

  async plan() {
    const cfg = loadConfig();
    const { problems, warnings } = audit(cfg);
    for (const w of warnings) console.log(`warn   ${w}`);
    for (const p of problems) console.log(`BLOCK  ${p}`);
    if (problems.length) die(`${problems.length} blocking problem(s). Nothing was sent.`, 2);

    console.log('about to: GET /accounts and GET /comment-automations, then print the diff. No writes.');
    const account = await resolveAccount(cfg);
    const profileId = await resolveProfileId(account, cfg);
    const live = (await api('GET', '/comment-automations')).automations || [];
    const byName = new Map(live.map((a) => [a.name, a]));

    console.log(`\naccount: ${account.username} (${accountIdOf(account)})  profile: ${profileId}\n`);
    for (const rule of cfg.automations) {
      const existing = byName.get(rule.name);
      const payload = buildPayload(rule, { accountId: accountIdOf(account), profileId });
      if (!existing) {
        console.log(`CREATE  ${rule.name}`);
      } else {
        console.log(`UPDATE  ${rule.name}  (id=${existing.id})`);
      }
      console.log(`        ${JSON.stringify(payload).slice(0, 400)}\n`);
    }
    const orphans = live.filter((a) => !cfg.automations.some((r) => r.name === a.name));
    for (const o of orphans) console.log(`ORPHAN  ${o.name} (id=${o.id}) is live but not in automations.json. Delete it by hand if it is stale.`);
  },

  async sync() {
    const cfg = loadConfig();
    const { problems, warnings } = audit(cfg);
    for (const w of warnings) console.log(`warn   ${w}`);
    if (problems.length) {
      for (const p of problems) console.log(`BLOCK  ${p}`);
      die(`${problems.length} blocking problem(s). Nothing was sent.`, 2);
    }
    if (!APPLY) {
      console.log('dry run. Re-run with --apply to write. Showing the plan:\n');
      return commands.plan();
    }

    console.log('about to: CREATE or PATCH automations on the live Instagram account.');
    const account = await resolveAccount(cfg);
    const profileId = await resolveProfileId(account, cfg);
    const live = (await api('GET', '/comment-automations')).automations || [];
    const byName = new Map(live.map((a) => [a.name, a]));

    for (const rule of cfg.automations) {
      const payload = buildPayload(rule, { accountId: accountIdOf(account), profileId });
      const existing = byName.get(rule.name);
      if (existing) {
        console.log(`PATCH  ${rule.name} (${existing.id})`);
        await api('PATCH', `/comment-automations/${existing.id}`, payload);
      } else {
        console.log(`POST   ${rule.name}`);
        const out = await api('POST', '/comment-automations', payload);
        console.log(`       created id=${out.id || out.automation?.id}`);
      }
    }
    console.log('\ndone. Run "node zernio.mjs list" to read back what is live.');
  },

  async get() {
    const id = positional[0];
    if (!id) die('usage: zernio.mjs get <automationId>');
    console.log(`about to: GET /comment-automations/${id} (read only).`);
    const out = await api('GET', `/comment-automations/${id}`);
    console.log(JSON.stringify(out, null, 2));
  },

  async logs() {
    const id = positional[0];
    if (!id) die('usage: zernio.mjs logs <automationId>');
    console.log(`about to: GET /comment-automations/${id}/logs (read only).`);
    const out = await api('GET', `/comment-automations/${id}/logs`);
    console.log(JSON.stringify(out, null, 2));
  },

  async pause() {
    const id = positional[0];
    if (!id) die('usage: zernio.mjs pause <automationId> --apply');
    console.log(`about to: PATCH /comment-automations/${id} isActive=false`);
    if (!APPLY) return console.log('dry run. Re-run with --apply.');
    await api('PATCH', `/comment-automations/${id}`, { isActive: false });
    console.log('paused.');
  },

  async resume() {
    const id = positional[0];
    if (!id) die('usage: zernio.mjs resume <automationId> --apply');
    console.log(`about to: PATCH /comment-automations/${id} isActive=true`);
    if (!APPLY) return console.log('dry run. Re-run with --apply.');
    await api('PATCH', `/comment-automations/${id}`, { isActive: true });
    console.log('resumed.');
  },

  async delete() {
    const id = positional[0];
    if (!id) die('usage: zernio.mjs delete <automationId> --apply --yes');
    if (!APPLY || !flags.has('--yes')) die('delete needs both --apply and --yes. Nothing was sent.');
    console.log(`about to: DELETE /comment-automations/${id}`);
    await api('DELETE', `/comment-automations/${id}`);
    console.log('deleted.');
  },
};

const HELP = `
zernio.mjs - MAKERS comment-to-DM control plane (Zernio)

  doctor              key check + connected accounts + config audit
  accounts            raw GET /accounts
  list                every live automation with its stats
  plan                diff automations.json against live. No writes.
  sync [--apply]      create/update from automations.json. Dry run without --apply.
  logs <id>           who commented, what they wrote, whether the DM went out
  pause <id> --apply
  resume <id> --apply
  delete <id> --apply --yes

key:    ${ENV_FILE}  (ZERNIO_API_KEY=sk_...)
config: ${CONFIG_FILE}
`;

// only run the CLI when this file is the entry point, so selfcheck.mjs can import audit().
const INVOKED_DIRECTLY = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (INVOKED_DIRECTLY) {
  if (!cmd || !commands[cmd]) {
    console.log(HELP);
    process.exit(cmd ? 1 : 0);
  }
  await commands[cmd]();
}
