#!/usr/bin/env node
// Read saved evidence only. No experiment imports, fitting, network, or audio.
// Usage: node check_saved_evidence.mjs --root REPO --out NEW_EMPTY_DIRECTORY
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
function option(name, fallback) {
  const index = argv.indexOf(name);
  return index < 0 ? fallback : argv[index + 1];
}
const root = path.resolve(option('--root', path.join(here, '../../..')));
const outArg = option('--out');
if (!outArg) throw new Error('Pass --out pointing to a new empty directory.');
const out = path.resolve(outArg);
if (out === root || root.startsWith(out + path.sep)) throw new Error('Unsafe output path.');
if (fs.existsSync(out) && fs.readdirSync(out).length) throw new Error('Output directory must be empty.');
const read = relative => fs.readFileSync(path.join(root, relative));
const readJSON = relative => JSON.parse(read(relative).toString('utf8'));
const sha256 = buffer => crypto.createHash('sha256').update(buffer).digest('hex');
const blobSha = buffer => crypto.createHash('sha1').update(`blob ${buffer.length}\0`).update(buffer).digest('hex');
const metadata = JSON.parse(fs.readFileSync(path.join(here, 'input_identifiers.json'), 'utf8'));
const inventory = JSON.parse(fs.readFileSync(path.join(here, 'source_inventory.json'), 'utf8'));
if (inventory.truncated || inventory.inspected_commit !== metadata.inspected_commit) throw new Error('Incomplete or mismatched inventory.');
const files = new Map(inventory.files.map(item => [item.path, item]));
const checks = metadata.inputs.map(item => {
  const bytes = read(item.path);
  const actual = blobSha(bytes);
  if (actual !== item.git_blob_sha || actual !== files.get(item.path)?.git_blob_sha) throw new Error(`Input changed: ${item.path}`);
  return {...item, sha256: sha256(bytes), bytes: bytes.length};
});
const frozenSums = new Map(read('SHA256SUMS').toString('utf8').trim().split('\n').map(line => {
  const [hash, filename] = line.split('  '); return [filename, hash];
}));
for (const item of checks) {
  if (frozenSums.has(item.path) && item.sha256 !== frozenSums.get(item.path)) throw new Error(`Original checksum mismatch: ${item.path}`);
}
const config = readJSON('work/accounts_results/frozen_config.json');
const summary = readJSON('work/accounts_results/summary.json');
const diagnostics = readJSON('work/accounts_results/posthoc_diagnostics.json');
const protocol = readJSON('work/accounts_results/protocol.json');
const examples = readJSON('review/experiment08/report_examples.json');
if (config.source_sha256['accounts_experiment.py'] !== checks.find(x => x.path === 'work/accounts_experiment.py').sha256) throw new Error('Runner source provenance mismatch.');
if (config.source_sha256['accounts_reader.py'] !== checks.find(x => x.path === 'work/accounts_reader.py').sha256) throw new Error('Reader source provenance mismatch.');
if (config.protocol_sha256 !== checks.find(x => x.path === 'work/accounts_results/protocol.json').sha256) throw new Error('Protocol hash mismatch.');
if (JSON.stringify(config.source_sha256) !== JSON.stringify(protocol.source_sha256)) throw new Error('Frozen source manifests disagree.');

function parseCSV(text) {
  const matrix = []; let row = [], field = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') {field += '"'; i++;}
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') {row.push(field); field = '';}
    else if (c === '\n') {row.push(field); matrix.push(row); row = []; field = '';}
    else if (c !== '\r') field += c;
  }
  if (quoted) throw new Error('Unterminated CSV quote.');
  if (field.length || row.length) {row.push(field); matrix.push(row);}
  const headers = matrix.shift();
  return {headers, rows: matrix.map(values => {
    if (values.length !== headers.length) throw new Error('CSV width mismatch.');
    return Object.fromEntries(headers.map((h, i) => [h, values[i]]));
  })};
}
const {headers, rows} = parseCSV(read('review/experiment08/primary_trials.csv').toString('utf8'));
if (rows.some(r => r.delay_s !== '16' || r.mode !== 'intact')) throw new Error('Unexpected primary condition.');
if (new Set(rows.map(r => `${r.query_id}/${r.method}`)).size !== rows.length) throw new Error('Duplicate primary query/method.');
function counts(selected) {
  return {n: selected.length, correct_singletons: selected.filter(x => x.correct_singleton === 'true').length,
    absent_false_accept: selected.filter(x => x.absent_false_accept === 'true').length,
    joint_best: selected.every(x => x.joint_best === '') ? null : selected.filter(x => x.joint_best === 'true').length};
}
const byMethod = Object.fromEntries([...new Set(rows.map(x => x.method))].map(method => [method, counts(rows.filter(x => x.method === method))]));
for (const [method, value] of Object.entries(byMethod)) {
  for (const metric of ['n', 'correct_singletons', 'absent_false_accept']) {
    if (value[metric] !== summary.primary_by_method[method][metric]) throw new Error(`Summary mismatch: ${method}/${metric}`);
  }
}
const accounts = rows.filter(x => x.method === 'accounts');
const byLength = Object.fromEntries([...new Set(accounts.map(x => x.length))].map(length => [length, counts(accounts.filter(x => x.length === length))]));
for (const [length, values] of Object.entries(byLength)) {
  for (const metric of ['n', 'correct_singletons', 'joint_best']) if (values[metric] !== summary.lengths[length][metric]) throw new Error(`Length summary mismatch: ${length}/${metric}`);
}
const byFamily = Object.fromEntries(Object.keys(summary.families).map(family => {
  const values = counts(accounts.filter(x => x.family === family));
  for (const metric of ['n', 'correct_singletons', 'joint_best']) if (values[metric] !== summary.families[family][metric]) throw new Error(`Family summary mismatch: ${family}/${metric}`);
  return [family, {...values, unique_top_score_true: diagnostics.families[family].unique_top_score_true}];
}));
const missing = [
  {path: 'work/accounts_results/development_pairs.json', purpose: 'Calibration candidate evidence/scores for e04-e07. Needed for leave-one-calibration-group-out threshold sensitivity.'},
  {path: 'work/accounts_results/held_out_pairs.json', purpose: 'Held-out candidate evidence/scores. Needed for true-source and maximum absent-history margins for 576 queries.'}
].map(item => ({...item, present_in_inspected_tree: files.has(item.path), present_in_local_root: fs.existsSync(path.join(root, item.path))}));
if (missing.some(item => item.present_in_inspected_tree || item.present_in_local_root)) throw new Error('Evidence availability changed. Continue the existing audit after inspecting the saved inputs; this blocker script must not substitute for it.');

// Only subtract the fixed threshold from logits already saved for accepted examples.
// No scoring of rejected examples, model evaluation, or alternate threshold calculation.
const exampleMargins = examples.map(example => {
  const trial = accounts.find(row => row.query_id === example.query_id);
  if (!trial) throw new Error('Example lacks corresponding primary row.');
  const sourceId = `${example.group_id}_reference_${trial.source}`;
  const accepted = example.accepted.find(candidate => candidate.memory_id === sourceId);
  return {query_id: example.query_id, group_id: example.group_id, length: Number(trial.length), family: example.family,
    saved_true_source_support_logit: accepted?.support_logit ?? null,
    fixed_threshold: config.threshold,
    saved_true_source_margin: accepted ? accepted.support_logit - config.threshold : null,
    maximum_absent_history_score: null, absent_history_margin: null,
    availability: accepted ? 'Accepted example only; no absent-history candidate scores' : 'Rejected example; no emitted support logit. Saved true-reference features are outside this partial calculation.'};
});
const result = {
  status: 'blocked_missing_saved_pairs', inspected_commit: metadata.inspected_commit,
  fixed_threshold: config.threshold,
  calibration_only_sensitivity: {status: 'not_computed', groups: ['e04', 'e05', 'e06', 'e07'], reason: 'Per-query calibration candidate scores/evidence unavailable. Aggregate 37 correct / 1 false acceptance out of 120 is insufficient.'},
  frozen_calibration_summary: config.calibration.accounts,
  held_out_margin_comparison: {status: 'not_computed', reason: 'Complete true-source and absent-history candidate scores unavailable.'},
  missing_inputs: missing,
  primary_csv_headers: headers,
  primary_csv_rows: rows.length,
  primary_unique_queries: new Set(accounts.map(x => x.query_id)).size,
  methods: byMethod, lengths: byLength, families: byFamily,
  unique_top_total_reported: Object.values(diagnostics.families).reduce((n, x) => n + x.unique_top_score_true, 0),
  published_example_margins: exampleMargins,
  scope: 'Deterministic saved-artifact checks and arithmetic only. No fitting, threshold replacement, audio generation/extraction, experiment execution, or confirmatory claims.'
};
fs.mkdirSync(out, {recursive: true});
fs.writeFileSync(path.join(out, 'evidence_tables.json'), JSON.stringify(result, null, 2) + '\n');
fs.writeFileSync(path.join(out, 'verified_inputs.json'), JSON.stringify({repository: metadata.repository, inspected_commit: metadata.inspected_commit, inputs: checks}, null, 2) + '\n');
console.log(JSON.stringify({status: result.status, fixed_threshold: config.threshold, verified_inputs: checks.length, primary_rows: rows.length, example_margins: exampleMargins.map(x => x.saved_true_source_margin)}, null, 2));
