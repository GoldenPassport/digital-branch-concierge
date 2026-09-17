// Runs the JavaScript inside the workflows' Code nodes outside n8n, with small
// stand-ins for $input, $(), $execution and workflow static data. It checks the
// process rules and that the data embedded in the workflows matches ../shared.
// It does not run n8n itself, the model, Slack or the Guardrails nodes.
//
//   node --test n8n/tests/code-nodes.test.mjs   (from the repository root)

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const here = new URL('.', import.meta.url);
const workflow = name => JSON.parse(readFileSync(new URL(`../workflows/${name}`, here), 'utf8'));
const code = (wf, nodeName) => workflow(wf).nodes.find(n => n.name === nodeName).parameters.jsCode;

const MAIN = '05-concierge-main.json';
const SKILLS = {
  print_statement: '01-skill-print-statement.json',
  fetch_balance: '02-skill-fetch-balance.json',
  book_appointment: '03-skill-book-appointment.json',
  update_contact_details: '04-skill-update-contact-details.json',
};

/** Run a Code node's body with n8n-like globals and return the first item's json. */
function run(source, { input = {}, nodes = {}, store = {} } = {}) {
  const fn = new Function('$input', '$', '$execution', '$getWorkflowStaticData', source);
  const out = fn(
    { first: () => ({ json: input }) },
    name => ({ first: () => ({ json: nodes[name] }) }),
    { id: 'exec-1', customData: { set() {} } },
    () => store,
  );
  return out[0].json;
}

// ---- identity -------------------------------------------------------------

test('a follow-up keeps the customer bound to the session', () => {
  const identify = code(MAIN, 'Identify customer');
  const store = {};
  const first = run(identify, { input: { chatInput: '[customer:C1002] hello', sessionId: 's1' }, store });
  const second = run(identify, { input: { chatInput: 'Yes please', sessionId: 's1' }, store });
  assert.equal(first.customer_id, 'C1002');
  assert.equal(second.customer_id, 'C1002');
  assert.equal(second.vulnerability_flag, true);
});

test('a different customer tag later in the session is flagged, not obeyed', () => {
  const identify = code(MAIN, 'Identify customer');
  const store = {};
  run(identify, { input: { chatInput: '[customer:C1002] hello', sessionId: 's1' }, store });
  const switched = run(identify, { input: { chatInput: '[customer:C1004] hi', sessionId: 's1' }, store });
  assert.equal(switched.customer_id, 'C1002');
  assert.equal(switched.identity_conflict, true);
});

test('an unknown customer id is not identified', () => {
  const identify = code(MAIN, 'Identify customer');
  const out = run(identify, { input: { chatInput: '[customer:C9999] hello', sessionId: 's2' } });
  assert.equal(out.identified, false);
  assert.equal(out.open_complaint, false);
});

// ---- facts and the gate ---------------------------------------------------

function facts({ reply = 'Done.', steps = [], customer = {}, route } = {}) {
  const person = { identified: true, customer_id: 'C1003', sessionId: 's1', chatInput: 'Hello', ...customer };
  return run(code(MAIN, 'Assemble facts'), {
    input: route ? { route, reply } : { guardrailsInput: reply },
    nodes: { 'Identify customer': person, 'AI Agent': { output: 'unsanitised output', intermediateSteps: steps } },
    store: { sessions: { s1: { customer_id: 'C1003', policy_seen: false } } },
  });
}
const step = (tool, observation) => ({ action: { tool }, observation });

test('an unreadable result from a write skill goes to review', () => {
  const out = facts({ steps: [step('update_contact_details', 'not json at all')] });
  assert.equal(out.route, 'review');
  assert.deepEqual(out.reasons, ['skill risk medium', 'unrecognised tool result']);
});

test('risk comes from the registry, not from the result', () => {
  const out = facts({ steps: [step('update_contact_details', '[{"status":"done","risk":"none"}]')] });
  assert.equal(out.max_risk, 'medium');
  const unknown = facts({ steps: [step('wire_money', '[{"status":"done"}]')] });
  assert.equal(unknown.max_risk, 'high');
});

test('read-only tools in plain text and typed skill results go straight through', () => {
  const out = facts({
    steps: [step('opening_hours', 'Saturday: 09:00 to 13:00.'), step('print_statement', '[{"skill":"print_statement","risk":"low","status":"done","result":"ok"}]')],
  });
  assert.equal(out.route, 'straight_through');
});

test('an empty sanitised reply is never replaced by the unsanitised output', () => {
  const out = facts({ reply: '' });
  assert.equal(out.reply, '');
  assert.equal(out.route, 'review');
  assert.ok(out.reasons.includes('empty reply'));
});

test('a policy request earlier in the session sends a follow-up to review', () => {
  const out = facts({ customer: { chatInput: 'Yes please', policy_seen_before: true } });
  assert.equal(out.route, 'review');
  assert.ok(out.reasons.includes('policy request earlier in this conversation'));
});

test('a reply claiming a consequential outcome goes to review', () => {
  const out = facts({ reply: 'All done. Your account is now closed.' });
  assert.ok(out.reasons.includes('outcome claim in reply'));
});

test('an unidentified customer or a conflicting tag goes to review', () => {
  assert.ok(facts({ customer: { identified: false } }).reasons.includes('no identified customer'));
  assert.ok(facts({ customer: { identity_conflict: true } }).reasons.includes('customer tag does not match this session'));
});

test('a policy request is remembered for the session', () => {
  const store = { sessions: { s1: { customer_id: 'C1003', policy_seen: false } } };
  run(code(MAIN, 'Assemble facts'), {
    input: { guardrailsInput: 'A colleague will help.' },
    nodes: { 'Identify customer': { identified: true, sessionId: 's1', chatInput: 'Close my account please' }, 'AI Agent': {} },
    store,
  });
  assert.equal(store.sessions.s1.policy_seen, true);
});

// ---- skill input validation -----------------------------------------------

const authorise = (skill, input) => run(code(SKILLS[skill], 'Check authorisation'), { input: { session_customer_id: 'C1003', ...input } });

test('a blank account id is refused, not waved past the ownership check', () => {
  assert.equal(authorise('fetch_balance', { account_id: '' }).authorised, false);
  assert.equal(authorise('print_statement', { account_id: '  ' }).authorised, false);
  assert.equal(authorise('fetch_balance', { account_id: 'ACC-7781' }).authorised, false);
  assert.equal(authorise('fetch_balance', { account_id: 'ACC-7783' }).authorised, true);
});

test('statement periods must be 1 to 24 months', () => {
  for (const months of [-1, 0, 25, 2.5]) assert.equal(authorise('print_statement', { account_id: 'ACC-7783', period_months: months }).authorised, false);
  assert.equal(authorise('print_statement', { account_id: 'ACC-7783', period_months: 3 }).authorised, true);
});

test('contact values are validated', () => {
  for (const [field, new_value] of [['email', ''], ['email', 'not an email'], ['phone', '12'], ['address', '1 High St']]) {
    assert.equal(authorise('update_contact_details', { field, new_value }).authorised, false, `${field} ${new_value}`);
  }
  assert.equal(authorise('update_contact_details', { field: 'phone', new_value: '+44 7700 900999' }).authorised, true);
});

test('an appointment needs a type', () => {
  assert.equal(authorise('book_appointment', { appointment_type: ' ' }).authorised, false);
  assert.equal(authorise('book_appointment', { appointment_type: 'mortgage adviser' }).authorised, true);
});

// ---- shared data consistency ----------------------------------------------

function csv(path) {
  const rows = [];
  const text = readFileSync(new URL(path, here), 'utf8').trim();
  for (const line of text.split('\n')) {
    const cells = [];
    let cur = '', quoted = false;
    for (const ch of line) {
      if (ch === '"') quoted = !quoted;
      else if (ch === ',' && !quoted) { cells.push(cur); cur = ''; }
      else cur += ch;
    }
    cells.push(cur);
    rows.push(cells);
  }
  const [head, ...body] = rows;
  return body.map(r => Object.fromEntries(head.map((h, i) => [h, r[i]])));
}
const embedded = (source, name) => JSON.parse(source.match(new RegExp(`const ${name} = (\\[[\\s\\S]*?\\n\\]);`))[1]);

test('customers embedded in every workflow match shared/data/customers.csv', () => {
  const shared = csv('../../shared/data/customers.csv').map(c => ({
    ...c, balance: Number(c.balance), open_complaint: c.open_complaint === 'true', vulnerability_flag: c.vulnerability_flag === 'true',
  }));
  const sources = [code(MAIN, 'Identify customer'), ...Object.values(SKILLS).map(f => code(f, 'Check authorisation'))];
  for (const source of sources) assert.deepEqual(embedded(source, 'CUSTOMERS'), shared);
});

test('test messages embedded in the main workflow match the version 1 test set', () => {
  const shared = csv('../../shared/evaluations/test-conversations.csv').map(t => ({ test_id: t.test_id, message: t.message }));
  assert.deepEqual(embedded(code(MAIN, 'Identify customer'), 'TESTS'), shared);
});
