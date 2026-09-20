#!/usr/bin/env node
// selfcheck.mjs - proves the audit blocks the dangerous shapes AND passes the real config.
// A gate that never reds is not a gate; a gate that reds a correct config teaches people to skip it.
// Run: node selfcheck.mjs

import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { audit } from './zernio.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
let failures = 0;

function check(label, cfg, expect) {
  const { problems, warnings } = audit(cfg);
  const gotBlock = problems.length > 0;
  const ok = expect.block === gotBlock && (!expect.match || problems.concat(warnings).some((p) => p.includes(expect.match)));
  console.log(`${ok ? 'pass' : 'FAIL'}  ${label}`);
  if (!ok) {
    failures++;
    console.log(`        expected block=${expect.block} match=${expect.match || '-'}`);
    console.log(`        problems: ${JSON.stringify(problems)}`);
    console.log(`        warnings: ${JSON.stringify(warnings)}`);
  }
}

const base = {
  name: 't',
  trigger: 'comment',
  keywords: ['מייקר'],
  matchMode: 'contains',
  dmMessage: 'hello',
  platformPostId: 'p1',
};

// --- must BLOCK -----------------------------------------------------------
check('short keyword on contains', { automations: [{ ...base, keywords: ['כן'] }] }, { block: true, match: 'Too short' });
check('shortened link in DM', { automations: [{ ...base, dmMessage: 'take it bit.ly/x' }] }, { block: true, match: 'shortener' });
check('DM over the button cap', { automations: [{ ...base, buttons: [{ type: 'url', title: 'a', url: 'https://x.co' }], dmMessage: 'x'.repeat(641) }] }, { block: true, match: 'over the 640' });
check('follower-only without gate copy', { automations: [{ ...base, audience: { followerStatus: 'follower' } }] }, { block: true, match: 'without followGate' });
check('keyword collision on same scope', { automations: [base, { ...base, name: 't2' }] }, { block: true, match: 'collides' });
check('no keywords', { automations: [{ ...base, keywords: [] }] }, { block: true, match: 'no keywords' });

// --- must WARN but not block ---------------------------------------------
check('account-wide rule warns only', { automations: [{ ...base, platformPostId: null }] }, { block: false, match: 'account-wide rule' });
check('keyword with a space warns only', { automations: [{ ...base, keywords: ['על הסדנה'] }] }, { block: false, match: 'contains a space' });

// --- your own config must PASS -------------------------------------------
// Before you have copied the example, this checks the example itself, so a fresh
// clone still proves the auditor runs end to end.
import { existsSync } from 'node:fs';
const mine = join(HERE, 'automations.json');
const target = existsSync(mine) ? mine : join(HERE, 'automations.example.json');
const real = JSON.parse(readFileSync(target, 'utf8'));
check(`${target.split('/').pop()} passes the audit`, real, { block: false });

console.log(failures ? `\n${failures} failure(s)` : '\nall green');
process.exit(failures ? 1 : 0);
