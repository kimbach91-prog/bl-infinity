import crypto from 'node:crypto';
import {
  generateRegistrationOptions,
  verifyRegistrationResponse,
  generateAuthenticationOptions,
  verifyAuthenticationResponse,
} from '@simplewebauthn/server';
import { db, one, many, storeChallenge, consumeChallenge, createSession, getSession, revokeSession, appendAudit, takeRate } from '../lib/db.mjs';
import {
  assertProductionSecrets, setSecurityHeaders, parseCookies, setSessionCookies, clearSessionCookies,
  assertOrigin, assertCsrf, sha256, timingSafeHexEqual, generateTotpSecret, verifyTotp,
  kmsEncrypt, kmsDecrypt, kmsSignDigest, randomToken, caSignNodeCsr,
} from '../lib/security.mjs';

const RP_NAME = 'DEUS Human OS';
const constitutionVersion = 'BL-CF Founding Constitution v0.4';
const scheduleVersion = 'DEUS Human OS Membership & Settlement Schedule v0.1';

function json(res, status, body) { return res.status(status).json(body); }
function routeOf(req) { return String(req.query?.route || '').replace(/^\/+|\/+$/g, ''); }
function body(req) { return req.body && typeof req.body === 'object' ? req.body : {}; }
function clientIp(req) { return req.headers['x-forwarded-for']?.split(',')[0]?.trim() || req.socket?.remoteAddress || 'unknown'; }
function rateKey(req, group) { return sha256(`${group}|${clientIp(req)}|${req.headers['user-agent'] || ''}`); }
async function limit(req, res, group, opts) { const r = await takeRate(rateKey(req, group), opts); if (!r.ok) { res.setHeader('Retry-After', String(r.retryAfterSeconds)); json(res, 429, { error: 'RATE_LIMITED' }); return false; } return true; }

async function requireSession(req, res, { aal = 1, mutate = false } = {}) {
  const token = parseCookies(req)['__Host-deus_session'];
  const session = await getSession(token);
  if (!session) { json(res, 401, { error: 'AUTH_REQUIRED' }); return null; }
  if (Number(session.aal) < aal) { json(res, 403, { error: 'STEP_UP_REQUIRED', requiredAal: aal }); return null; }
  if (mutate) { assertOrigin(req); assertCsrf(req, session); }
  return { token, session };
}

async function health(res) {
  const required = ['DATABASE_URL','DEUS_RP_ID','DEUS_ORIGIN','DEUS_FOUNDER_EMAIL','DEUS_BOOTSTRAP_TOKEN_SHA256','DEUS_KMS_SIGN_URL','DEUS_KMS_ENCRYPT_URL','DEUS_KMS_DECRYPT_URL','DEUS_KMS_KEY_ID','DEUS_CA_SIGN_URL'];
  const missing = required.filter((k) => !process.env[k]);
  let database = false;
  try { if (process.env.DATABASE_URL) { await one('SELECT 1 AS ok'); database = true; } } catch {}
  return json(res, missing.length || !database ? 503 : 200, {
    ok: missing.length === 0 && database,
    service: 'deus-human-os-gateway',
    version: '0.2.0-r2',
    securityMode: process.env.DEUS_SECURITY_MODE || 'production',
    database,
    kmsConfigured: Boolean(process.env.DEUS_KMS_SIGN_URL && process.env.DEUS_KMS_ENCRYPT_URL && process.env.DEUS_KMS_DECRYPT_URL),
    caConfigured: Boolean(process.env.DEUS_CA_SIGN_URL),
    missing,
    controls: { webauthn: true, mfa: true, serverSessions: true, csrf: true, signedReceipts: true, appendOnlyAudit: true, nodeEnrollment: true, failClosed: true }
  });
}

async function bootstrapOptions(req, res) {
  assertProductionSecrets();
  if (!await limit(req, res, 'bootstrap-options', { capacity: 5, refillPerSecond: 1/60 })) return;
  const supplied = String(req.headers['x-deus-bootstrap-token'] || '');
  if (!timingSafeHexEqual(sha256(supplied), process.env.DEUS_BOOTSTRAP_TOKEN_SHA256)) return json(res, 403, { error: 'BOOTSTRAP_DENIED' });
  const count = Number((await one('SELECT count(*)::int AS n FROM hos_users'))?.n || 0);
  if (count !== 0) return json(res, 409, { error: 'BOOTSTRAP_CLOSED' });
  const email = String(body(req).email || '').trim().toLowerCase();
  if (!email || email !== String(process.env.DEUS_FOUNDER_EMAIL).toLowerCase()) return json(res, 403, { error: 'FOUNDER_SUBJECT_MISMATCH' });
  const userId = `usr_${randomToken(18)}`;
  const options = await generateRegistrationOptions({
    rpName: RP_NAME,
    rpID: process.env.DEUS_RP_ID,
    userID: Buffer.from(userId, 'utf8'),
    userName: email,
    userDisplayName: 'Founding Steward',
    attestationType: 'direct',
    authenticatorSelection: { residentKey: 'required', userVerification: 'required' },
    supportedAlgorithmIDs: [-7, -257],
  });
  const challengeId = await storeChallenge('bootstrap-webauthn', email, options.challenge, { userId }, 300);
  await appendAudit(null, 'auth.bootstrap-options', { emailHash: sha256(email), challengeId });
  return json(res, 200, { challengeId, options });
}

async function bootstrapVerify(req, res) {
  assertProductionSecrets(); assertOrigin(req);
  if (!await limit(req, res, 'bootstrap-verify', { capacity: 5, refillPerSecond: 1/60 })) return;
  const supplied = String(req.headers['x-deus-bootstrap-token'] || '');
  if (!timingSafeHexEqual(sha256(supplied), process.env.DEUS_BOOTSTRAP_TOKEN_SHA256)) return json(res, 403, { error: 'BOOTSTRAP_DENIED' });
  const input = body(req);
  const challenge = await consumeChallenge(input.challengeId, 'bootstrap-webauthn');
  if (!challenge) return json(res, 400, { error: 'CHALLENGE_INVALID' });
  const count = Number((await one('SELECT count(*)::int AS n FROM hos_users'))?.n || 0);
  if (count !== 0) return json(res, 409, { error: 'BOOTSTRAP_CLOSED' });
  const verification = await verifyRegistrationResponse({ response: input.response, expectedChallenge: challenge.challenge, expectedOrigin: process.env.DEUS_ORIGIN, expectedRPID: process.env.DEUS_RP_ID, requireUserVerification: true });
  if (!verification.verified || !verification.registrationInfo?.credential) return json(res, 401, { error: 'PASSKEY_VERIFICATION_FAILED' });
  const info = verification.registrationInfo;
  const cred = info.credential;
  const userId = challenge.context.userId;
  const email = challenge.subject;
  const totpSecret = generateTotpSecret();
  const encrypted = await kmsEncrypt(totpSecret);
  const client = await db().connect();
  try {
    await client.query('BEGIN');
    await client.query(`INSERT INTO hos_users(id,email,display_name,role) VALUES($1,$2,'Founding Steward','founder')`, [userId,email]);
    await client.query(`INSERT INTO hos_webauthn_credentials(credential_id,user_id,public_key,counter,transports,device_type,backed_up) VALUES($1,$2,$3,$4,$5,$6,$7)`, [cred.id,userId,Buffer.from(cred.publicKey),cred.counter || 0,JSON.stringify(cred.transports || []),info.credentialDeviceType || null,Boolean(info.credentialBackedUp)]);
    await client.query(`INSERT INTO hos_totp(user_id,secret_ciphertext,kms_key_id,enabled) VALUES($1,$2,$3,false)`, [userId,encrypted.ciphertext,encrypted.keyId]);
    await client.query('COMMIT');
  } catch (e) { await client.query('ROLLBACK'); throw e; } finally { client.release(); }
  const mfaTicket = await storeChallenge('bootstrap-mfa', userId, randomToken(24), {}, 300);
  await appendAudit(userId, 'auth.founder-passkey-enrolled', { credentialIdHash: sha256(cred.id), deviceType: info.credentialDeviceType || null, backedUp: Boolean(info.credentialBackedUp) });
  const issuer = encodeURIComponent('DEUS Human OS');
  const label = encodeURIComponent(`DEUS:${email}`);
  const otpauth = `otpauth://totp/${label}?secret=${totpSecret}&issuer=${issuer}&algorithm=SHA1&digits=6&period=30`;
  return json(res, 200, { mfaTicket, otpauth, secret: totpSecret, warning: 'Display once. Do not log or persist this plaintext TOTP secret.' });
}

async function bootstrapMfaVerify(req, res) {
  assertProductionSecrets(); assertOrigin(req);
  if (!await limit(req, res, 'bootstrap-mfa', { capacity: 8, refillPerSecond: 1/30 })) return;
  const input = body(req);
  const challenge = await one(`SELECT * FROM hos_challenges WHERE id=$1 AND kind='bootstrap-mfa' AND consumed_at IS NULL AND expires_at>now()`, [input.mfaTicket]);
  if (!challenge) return json(res, 400, { error: 'MFA_TICKET_INVALID' });
  const record = await one('SELECT * FROM hos_totp WHERE user_id=$1', [challenge.subject]);
  const secret = await kmsDecrypt(record.secret_ciphertext);
  if (!verifyTotp(secret, input.code)) return json(res, 401, { error: 'MFA_INVALID' });
  await db().query('UPDATE hos_challenges SET consumed_at=now() WHERE id=$1 AND consumed_at IS NULL', [input.mfaTicket]);
  await db().query('UPDATE hos_totp SET enabled=true, verified_at=now() WHERE user_id=$1', [challenge.subject]);
  const session = await createSession(challenge.subject, 2, req);
  setSessionCookies(res, session.token, session.csrf, session.ttlSeconds);
  await appendAudit(challenge.subject, 'auth.bootstrap-complete', { aal: 2 });
  return json(res, 200, { ok: true, aal: 2, csrf: session.csrf, actionRequired: 'REMOVE_DEUS_BOOTSTRAP_TOKEN_SHA256' });
}

async function loginOptions(req, res) {
  assertProductionSecrets();
  if (!await limit(req, res, 'login-options', { capacity: 12, refillPerSecond: 0.2 })) return;
  const email = String(body(req).email || '').trim().toLowerCase();
  const user = await one(`SELECT * FROM hos_users WHERE email=$1 AND status='active'`, [email]);
  if (!user) return json(res, 200, { challengeId: randomToken(18), options: await generateAuthenticationOptions({ rpID: process.env.DEUS_RP_ID, userVerification: 'required', allowCredentials: [] }) });
  const creds = await many('SELECT credential_id, transports FROM hos_webauthn_credentials WHERE user_id=$1', [user.id]);
  const options = await generateAuthenticationOptions({ rpID: process.env.DEUS_RP_ID, userVerification: 'required', allowCredentials: creds.map((c) => ({ id: c.credential_id, transports: c.transports || [] })) });
  const challengeId = await storeChallenge('login-webauthn', user.id, options.challenge, {}, 300);
  return json(res, 200, { challengeId, options });
}

async function loginVerify(req, res) {
  assertProductionSecrets(); assertOrigin(req);
  if (!await limit(req, res, 'login-verify', { capacity: 10, refillPerSecond: 0.15 })) return;
  const input = body(req);
  const challenge = await consumeChallenge(input.challengeId, 'login-webauthn');
  if (!challenge) return json(res, 400, { error: 'CHALLENGE_INVALID' });
  const stored = await one('SELECT * FROM hos_webauthn_credentials WHERE credential_id=$1 AND user_id=$2', [input.response?.id, challenge.subject]);
  if (!stored) return json(res, 401, { error: 'PASSKEY_UNKNOWN' });
  const verification = await verifyAuthenticationResponse({
    response: input.response,
    expectedChallenge: challenge.challenge,
    expectedOrigin: process.env.DEUS_ORIGIN,
    expectedRPID: process.env.DEUS_RP_ID,
    credential: { id: stored.credential_id, publicKey: new Uint8Array(stored.public_key), counter: Number(stored.counter), transports: stored.transports || [] },
    requireUserVerification: true,
  });
  if (!verification.verified) return json(res, 401, { error: 'PASSKEY_VERIFICATION_FAILED' });
  await db().query('UPDATE hos_webauthn_credentials SET counter=$1,last_used_at=now() WHERE credential_id=$2', [verification.authenticationInfo.newCounter, stored.credential_id]);
  const mfaTicket = await storeChallenge('login-mfa', challenge.subject, randomToken(24), {}, 300);
  await appendAudit(challenge.subject, 'auth.passkey-ok', { credentialIdHash: sha256(stored.credential_id) });
  return json(res, 200, { mfaRequired: true, mfaTicket });
}

async function loginMfaVerify(req, res) {
  assertProductionSecrets(); assertOrigin(req);
  if (!await limit(req, res, 'login-mfa', { capacity: 10, refillPerSecond: 0.15 })) return;
  const input = body(req);
  const challenge = await one(`SELECT * FROM hos_challenges WHERE id=$1 AND kind='login-mfa' AND consumed_at IS NULL AND expires_at>now()`, [input.mfaTicket]);
  if (!challenge) return json(res, 400, { error: 'MFA_TICKET_INVALID' });
  const record = await one(`SELECT * FROM hos_totp WHERE user_id=$1 AND enabled=true`, [challenge.subject]);
  if (!record) return json(res, 403, { error: 'MFA_NOT_ENROLLED' });
  const secret = await kmsDecrypt(record.secret_ciphertext);
  if (!verifyTotp(secret, input.code)) return json(res, 401, { error: 'MFA_INVALID' });
  await db().query('UPDATE hos_challenges SET consumed_at=now() WHERE id=$1 AND consumed_at IS NULL', [input.mfaTicket]);
  const session = await createSession(challenge.subject, 2, req);
  setSessionCookies(res, session.token, session.csrf, session.ttlSeconds);
  await appendAudit(challenge.subject, 'auth.session-created', { aal: 2 });
  return json(res, 200, { ok: true, aal: 2, csrf: session.csrf });
}

async function me(req, res) {
  const auth = await requireSession(req, res); if (!auth) return;
  return json(res, 200, { user: { id: auth.session.user_id, email: auth.session.email, role: auth.session.role }, aal: Number(auth.session.aal) });
}
async function logout(req, res) {
  const auth = await requireSession(req, res, { mutate: true }); if (!auth) return;
  await revokeSession(auth.token); clearSessionCookies(res); await appendAudit(auth.session.user_id, 'auth.logout', {}); return json(res, 200, { ok: true });
}

async function acceptConstitution(req, res) {
  const auth = await requireSession(req, res, { aal: 2, mutate: true }); if (!auth) return;
  const input = body(req);
  const payload = { userId: auth.session.user_id, constitutionVersion, scheduleVersion, acceptedAt: new Date().toISOString(), terms: input.terms, clientEvidence: input.clientEvidence || null };
  const payloadHash = sha256(JSON.stringify(payload));
  const signed = await kmsSignDigest(payloadHash);
  const receiptId = `rcpt_${randomToken(18)}`;
  await db().query('INSERT INTO hos_constitution_receipts(receipt_id,user_id,constitution_version,schedule_version,payload,payload_hash,signature,signing_key_id) VALUES($1,$2,$3,$4,$5,$6,$7,$8)', [receiptId,auth.session.user_id,constitutionVersion,scheduleVersion,payload,payloadHash,signed.signature,signed.keyId]);
  await appendAudit(auth.session.user_id, 'constitution.accepted', { receiptId, payloadHash, keyId: signed.keyId });
  return json(res, 201, { receiptId, payloadHash, signature: signed.signature, signingKeyId: signed.keyId });
}

function posturePass(posture = {}) {
  return posture.tpmPresent === true && posture.secureBoot === true && posture.diskEncryption === true && posture.firewall === true && posture.antimalware === true && posture.privateKeyNonExportable === true;
}
async function enrollNode(req, res) {
  const auth = await requireSession(req, res, { aal: 2, mutate: true }); if (!auth) return;
  const input = body(req);
  const receipt = await one('SELECT receipt_id FROM hos_constitution_receipts WHERE receipt_id=$1 AND user_id=$2', [input.receiptId,auth.session.user_id]);
  if (!receipt) return json(res, 403, { error: 'RECEIPT_REQUIRED' });
  if (!input.csrPem || !String(input.csrPem).includes('BEGIN CERTIFICATE REQUEST')) return json(res, 400, { error: 'CSR_REQUIRED' });
  if (!posturePass(input.posture)) return json(res, 403, { error: 'DEVICE_POSTURE_REJECTED' });
  const grant = { eligibleIdleComputeCap: Math.min(0.10, Number(input.grant?.eligibleIdleComputeCap ?? 0.10)), localWorkloadPriority: true, revocable: true, arbitraryInboundShell: false, dataPolicy: input.grant?.dataPolicy || 'local' };
  const enrollmentId = `node_${randomToken(18)}`;
  const cert = await caSignNodeCsr({ enrollmentId, csrPem: input.csrPem, subject: auth.session.user_id, nodeName: input.nodeName, posture: input.posture, grant });
  await db().query(`INSERT INTO hos_node_enrollments(enrollment_id,user_id,receipt_id,node_name,csr_pem,posture,grant,certificate_chain_pem,certificate_serial,status,activated_at) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,'active',now())`, [enrollmentId,auth.session.user_id,input.receiptId,input.nodeName || 'Unnamed Node',input.csrPem,input.posture,grant,cert.certificateChainPem,cert.serial]);
  await appendAudit(auth.session.user_id, 'node.enrolled', { enrollmentId, serial: cert.serial, grant });
  return json(res, 201, { enrollmentId, certificateChainPem: cert.certificateChainPem, serial: cert.serial, grant });
}

export default async function handler(req, res) {
  setSecurityHeaders(res);
  try {
    const r = routeOf(req);
    if (req.method === 'GET' && r === 'health') return health(res);
    if (req.method === 'POST' && r === 'auth/bootstrap/options') return bootstrapOptions(req,res);
    if (req.method === 'POST' && r === 'auth/bootstrap/verify') return bootstrapVerify(req,res);
    if (req.method === 'POST' && r === 'auth/bootstrap/mfa/verify') return bootstrapMfaVerify(req,res);
    if (req.method === 'POST' && r === 'auth/login/options') return loginOptions(req,res);
    if (req.method === 'POST' && r === 'auth/login/verify') return loginVerify(req,res);
    if (req.method === 'POST' && r === 'auth/mfa/verify') return loginMfaVerify(req,res);
    if (req.method === 'GET' && r === 'session') return me(req,res);
    if (req.method === 'POST' && r === 'auth/logout') return logout(req,res);
    if (req.method === 'POST' && r === 'constitution/acceptances') return acceptConstitution(req,res);
    if (req.method === 'POST' && r === 'nodes/enroll') return enrollNode(req,res);
    return json(res, 404, { error: 'NOT_FOUND' });
  } catch (error) {
    const code = String(error.message || 'INTERNAL_ERROR');
    const status = /REJECTED|REQUIRED|MISMATCH|INVALID|DENIED/.test(code) ? 403 : /SECURITY_CONFIG_INCOMPLETE|KMS_|WORKLOAD_IDENTITY|DATABASE_URL/.test(code) ? 503 : 500;
    return json(res, status, { error: code, failClosed: true });
  }
}
