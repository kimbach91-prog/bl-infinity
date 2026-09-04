import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const script = readFileSync(resolve(here, '../backup-dual-drive.ps1'), 'utf8');
const docs = readFileSync(resolve(here, '../DUAL_ACCOUNT_BACKUP.md'), 'utf8');

function remoteVerbPresent(name) {
  const re = new RegExp(`['\"]${name}['\"]|\\brclone\\s+${name}\\b`, 'i');
  return re.test(script);
}

test('backup path uses copy, never remote destructive verbs', () => {
  assert.equal(remoteVerbPresent('copy'), true);
  for (const verb of ['sync', 'move', 'delete', 'deletefile', 'purge', 'rmdir', 'cleanup']) {
    assert.equal(remoteVerbPresent(verb), false, `remote destructive verb present: ${verb}`);
  }
});

test('source and destination remotes must be distinct', () => {
  assert.match(script, /SourceRemote\s+-eq\s+\$DestinationRemote/);
  assert.match(script, /must be different rclone remotes/i);
});

test('Google native files are materialized and not re-imported', () => {
  assert.match(script, /--drive-export-formats/);
  assert.match(script, /docx,xlsx,pptx,svg,pdf/);
  assert.doesNotMatch(script, /--drive-import-formats/);
});

test('destination upload is immutable and content is read back', () => {
  assert.match(script, /--immutable/);
  assert.match(script, /['\"]check['\"]/);
  assert.match(script, /--download/);
  assert.match(script, /--one-way/);
});

test('materialized files receive a SHA-256 manifest', () => {
  assert.match(script, /Get-FileHash[^\n]+SHA256/);
  assert.match(script, /__BL_BACKUP_MANIFEST\.json/);
  assert.match(script, /VERIFIED_MATERIALIZED_SNAPSHOT/);
});

test('full-drive capture requires explicit ROOT token', () => {
  assert.match(script, /requestedPath\s+-eq\s+['\"]ROOT['\"]/);
  assert.match(docs, /`ROOT` is an explicit token for the whole source Drive/);
});

test('remote identity truth boundary is explicit', () => {
  assert.match(script, /does not prove the human-readable remote aliases correspond to particular Google accounts/i);
  assert.match(docs, /Remote aliases are local labels only/i);
});

test('only local staging is removed after success', () => {
  const removeLines = script.split(/\r?\n/).filter((line) => /Remove-Item/i.test(line));
  assert.ok(removeLines.length > 0);
  for (const line of removeLines) {
    assert.match(line, /runStageRoot/);
    assert.doesNotMatch(line, /SourceRemote|DestinationRemote|rclone/i);
  }
});
