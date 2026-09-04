import test from 'node:test';
import assert from 'node:assert/strict';
import { openPostgresComputeTreasury } from '../lib/postgres-compute-treasury.mjs';

const connectionString = process.env.BL_TEST_POSTGRES_URL;

test('durable DCT/DCC ledger enforces backing, balances, idempotency, hash chain and freeze', { skip: !connectionString }, async () => {
  const treasury = await openPostgresComputeTreasury({ connectionString, applySchema: true });
  try {
    await treasury.pool.query('TRUNCATE federation_dcc_ledger, federation_dcc_accounts, federation_treasury_backing RESTART IDENTITY CASCADE');
    await treasury.pool.query(`
      UPDATE federation_treasury_settings
      SET reserved_liabilities_usd=0, dcc_min_backing_ratio=1.20, dcc_unit_value_usd=1,
          emergency_freeze=false, freeze_reason=NULL, updated_at=now()
      WHERE singleton=true
    `);

    await treasury.addBacking({
      backingType: 'cash',
      sourceRef: 'cash:test:120',
      faceValueUsd: 120,
      metadata: { fixture: true },
    });

    let status = await treasury.status();
    assert.equal(status.availableBackingUsd, 120);
    assert.equal(status.dccMinBackingRatio, 1.2);
    assert.equal(status.maximumDccOutstanding, 100);

    const minted = await treasury.mint({
      accountId: 'alice',
      amountDcc: 100,
      authorizationRef: 'auth:mint:alice',
      reference: 'pilot-credit',
      idempotencyKey: 'mint:alice:100',
    });
    assert.equal(minted.accountBalanceDcc, 100);
    assert.equal(minted.treasury.dccOutstanding, 100);
    assert.equal(minted.treasury.backingRatio, 1.2);

    const replay = await treasury.mint({
      accountId: 'alice',
      amountDcc: 100,
      authorizationRef: 'auth:mint:alice',
      reference: 'pilot-credit',
      idempotencyKey: 'mint:alice:100',
    });
    assert.equal(replay.idempotentReplay, true);
    assert.equal((await treasury.status()).dccOutstanding, 100);

    await assert.rejects(
      () => treasury.mint({
        accountId: 'alice', amountDcc: 1, authorizationRef: 'auth:mint:extra', idempotencyKey: 'mint:alice:extra',
      }),
      (error) => error.code === 'DCC_BACKING_INSUFFICIENT',
    );

    const transferred = await treasury.transfer({
      fromAccount: 'alice',
      toAccount: 'bob',
      amountDcc: 20,
      authorizationRef: 'auth:transfer:1',
      idempotencyKey: 'transfer:alice:bob:20',
    });
    assert.equal(transferred.fromBalanceDcc, 80);
    assert.equal(transferred.toBalanceDcc, 20);

    const redeemed = await treasury.redeem({
      accountId: 'bob',
      amountDcc: 10,
      authorizationRef: 'auth:redeem:bob:10',
      reference: 'compute-service-consumed',
      idempotencyKey: 'redeem:bob:10',
    });
    assert.equal(redeemed.accountBalanceDcc, 10);
    assert.equal(redeemed.treasury.dccOutstanding, 90);

    const chain = await treasury.verifyLedger();
    assert.equal(chain.ok, true);
    assert.equal(chain.records, 3);

    const [backing] = await treasury.listBacking();
    const revoked = await treasury.revokeBacking(backing.backingId, 'fixture-revocation');
    assert.equal(revoked.treasury.availableBackingUsd, 0);
    assert.equal(revoked.treasury.emergencyFreeze, true);
    assert.equal(revoked.treasury.freezeReason, 'automatic-undercollateralization-freeze');

    await assert.rejects(
      () => treasury.transfer({
        fromAccount: 'alice', toAccount: 'bob', amountDcc: 1,
        authorizationRef: 'auth:blocked-transfer', idempotencyKey: 'transfer:blocked',
      }),
      (error) => error.code === 'DCC_TREASURY_FROZEN',
    );

    // Burn/redemption remains available during a treasury freeze so liabilities can shrink.
    const frozenRedeem = await treasury.redeem({
      accountId: 'bob', amountDcc: 10,
      authorizationRef: 'auth:redeem:bob:rest', idempotencyKey: 'redeem:bob:rest',
    });
    assert.equal(frozenRedeem.accountBalanceDcc, 0);
    assert.equal(frozenRedeem.treasury.dccOutstanding, 80);

    await treasury.addBacking({ backingType: 'cash', sourceRef: 'cash:test:recovery', faceValueUsd: 120 });
    status = await treasury.setEmergencyFreeze(false, 'recovered');
    assert.equal(status.emergencyFreeze, false);
    assert.ok(status.backingRatio >= status.dccMinBackingRatio);

    const finalChain = await treasury.verifyLedger();
    assert.equal(finalChain.ok, true);
    assert.equal(finalChain.records, 4);
  } finally {
    await treasury.close();
  }
});

test('backing haircut and reserved liabilities reduce DCC minting capacity', { skip: !connectionString }, async () => {
  const treasury = await openPostgresComputeTreasury({ connectionString, applySchema: true });
  try {
    await treasury.pool.query('TRUNCATE federation_dcc_ledger, federation_dcc_accounts, federation_treasury_backing RESTART IDENTITY CASCADE');
    await treasury.pool.query(`
      UPDATE federation_treasury_settings
      SET reserved_liabilities_usd=0, dcc_min_backing_ratio=1.20, dcc_unit_value_usd=1,
          emergency_freeze=false, freeze_reason=NULL, updated_at=now()
      WHERE singleton=true
    `);
    await treasury.addBacking({ backingType: 'compute', sourceRef: 'compute:test:100', faceValueUsd: 100, haircutRate: 0.20 });
    await treasury.setReservedLiabilitiesUsd(20);
    const status = await treasury.status();
    assert.equal(status.effectiveBackingUsd, 80);
    assert.equal(status.availableBackingUsd, 60);
    assert.equal(status.maximumDccOutstanding, 50);
  } finally {
    await treasury.close();
  }
});
