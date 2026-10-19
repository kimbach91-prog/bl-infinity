/**
 * Public single-target fencing SHADOW, no production admission or quorum.
 * Never interpret a shadow receipt as authority to execute against a live Brain.
 */
import { DatabaseSync } from 'node:sqlite';
import { createHash } from 'node:crypto';

const hash = x => createHash('sha256').update(x).digest('hex');
const error = code => Object.assign(new Error(code), { code });
function canonical(x,seen=new Set()) {
  if (x===null || typeof x==='string' || typeof x==='boolean') return JSON.stringify(x);
  if (typeof x==='number' && Number.isFinite(x)) return JSON.stringify(x);
  if (typeof x!=='object' || seen.has(x)) throw error('INVALID_PAYLOAD');
  seen.add(x);
  let out;
  if (Array.isArray(x)) out='['+x.map(v=>canonical(v,seen)).join(',')+']';
  else {
    if (Object.getPrototypeOf(x)!==Object.prototype && Object.getPrototypeOf(x)!==null) throw error('INVALID_PAYLOAD');
    out='{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k],seen)).join(',')+'}';
  }
  seen.delete(x);
  return out;
}
function id(x) {
  if (typeof x!=='string' || !/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(x)) throw error('INVALID_ID');
  return x;
}
function integer(x) {
  if (!Number.isSafeInteger(x) || x<0) throw error('INVALID_EPOCH_OR_CLOCK');
  return x;
}
export class ShadowTargetFence {
  constructor(path) {
    this.db=new DatabaseSync(path);
    this.db.exec("PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA busy_timeout=5000;"+
      "CREATE TABLE IF NOT EXISTS shadow_leases(resource TEXT PRIMARY KEY,owner TEXT NOT NULL,epoch INTEGER NOT NULL,expires_at INTEGER NOT NULL);"+
      "CREATE TABLE IF NOT EXISTS shadow_effects(effect_seq INTEGER PRIMARY KEY AUTOINCREMENT,resource TEXT NOT NULL,request_id TEXT NOT NULL,owner TEXT NOT NULL,epoch INTEGER NOT NULL,payload_hash TEXT NOT NULL,receipt_json TEXT NOT NULL,UNIQUE(resource,request_id));"+
      "CREATE TABLE IF NOT EXISTS shadow_events(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,body_json TEXT NOT NULL,prev_hash TEXT NOT NULL,hash TEXT NOT NULL);");
  }
  #tx(fn) {
    this.db.exec('BEGIN IMMEDIATE');
    try {const result=fn();this.db.exec('COMMIT');return result;}
    catch(e) {this.db.exec('ROLLBACK');throw e;}
  }
  #event(kind,body) {
    const prev=this.db.prepare('SELECT hash FROM shadow_events ORDER BY seq DESC LIMIT 1').get()?.hash??'0'.repeat(64);
    const bodyJson=canonical(body),digest=hash([prev,kind,bodyJson].join('\n'));
    this.db.prepare('INSERT INTO shadow_events(kind,body_json,prev_hash,hash) VALUES(?,?,?,?)').run(kind,bodyJson,prev,digest);
  }
  claim({resource,owner,epoch,expiresAt,now=Date.now()}) {
    id(resource);id(owner);integer(epoch);integer(expiresAt);integer(now);
    if(epoch===0||expiresAt<=now)throw error('INVALID_OR_EXPIRED_LEASE');
    return this.#tx(()=>{
      const existing=this.db.prepare('SELECT epoch FROM shadow_leases WHERE resource=?').get(resource);
      if(existing&&epoch<=existing.epoch)throw error('STALE_OR_DUPLICATE_EPOCH');
      this.db.prepare('INSERT INTO shadow_leases(resource,owner,epoch,expires_at) VALUES(?,?,?,?) ON CONFLICT(resource) DO UPDATE SET owner=excluded.owner,epoch=excluded.epoch,expires_at=excluded.expires_at').run(resource,owner,epoch,expiresAt);
      this.#event('LEASE',{resource,owner,epoch,expiresAt});
      return {resource,owner,epoch,expiresAt,shadowOnly:true};
    });
  }
  apply({resource,owner,epoch,requestId,payload,now=Date.now()}) {
    id(resource);id(owner);id(requestId);integer(epoch);integer(now);
    const value=canonical(payload);
    if(Buffer.byteLength(value)>65536)throw error('PAYLOAD_TOO_LARGE');
    const payloadHash=hash(value);
    return this.#tx(()=>{
      const lease=this.db.prepare('SELECT * FROM shadow_leases WHERE resource=?').get(resource);
      if(!lease||lease.owner!==owner||lease.epoch!==epoch)throw error('STALE_FENCE_AT_TARGET');
      if(lease.expires_at<=now)throw error('EXPIRED_FENCE_AT_TARGET');
      const old=this.db.prepare('SELECT * FROM shadow_effects WHERE resource=? AND request_id=?').get(resource,requestId);
      if(old){
        if(old.owner!==owner||old.epoch!==epoch||old.payload_hash!==payloadHash)throw error('IDEMPOTENCY_CONFLICT');
        return {receipt:JSON.parse(old.receipt_json),reused:true};
      }
      const inserted=this.db.prepare('INSERT INTO shadow_effects(resource,request_id,owner,epoch,payload_hash,receipt_json) VALUES(?,?,?,?,?,?)').run(resource,requestId,owner,epoch,payloadHash,'{}');
      const core={schema:'shadow-target-fence-receipt/1',resource,owner,epoch,requestId,effectSeq:Number(inserted.lastInsertRowid),payloadHash,shadowOnly:true};
      const receipt={...core,receiptHash:hash(canonical(core))};
      this.db.prepare('UPDATE shadow_effects SET receipt_json=? WHERE effect_seq=?').run(canonical(receipt),receipt.effectSeq);
      this.#event('APPLY',receipt);
      return {receipt,reused:false};
    });
  }
  snapshot() {
    return {
      leases:this.db.prepare('SELECT * FROM shadow_leases ORDER BY resource').all(),
      effects:this.db.prepare('SELECT * FROM shadow_effects ORDER BY effect_seq').all(),
      events:this.db.prepare('SELECT * FROM shadow_events ORDER BY seq').all()
    };
  }
  close(){this.db.close();}
}