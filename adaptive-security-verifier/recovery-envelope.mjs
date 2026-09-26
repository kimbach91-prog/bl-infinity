import crypto from 'node:crypto';

const b64=b=>Buffer.from(b).toString('base64');
const unb64=s=>Buffer.from(String(s),'base64');

export function sealRecoveryEnvelope({plaintext,recipients,context='DEUS_OWNER_VAULT_RECOVERY_V1'}={}){
  if(!Array.isArray(recipients)||recipients.length<1)throw new Error('RECIPIENTS_REQUIRED');
  const dataKey=crypto.randomBytes(32),iv=crypto.randomBytes(12);
  const cipher=crypto.createCipheriv('aes-256-gcm',dataKey,iv);cipher.setAAD(Buffer.from(context));
  const ciphertext=Buffer.concat([cipher.update(Buffer.from(String(plaintext),'utf8')),cipher.final()]),tag=cipher.getAuthTag();
  const wrapped=recipients.map(r=>{
    if(!r?.id||!r?.publicKeyPem)throw new Error('INVALID_RECIPIENT');
    const key=crypto.publicEncrypt({key:r.publicKeyPem,oaepHash:'sha256',padding:crypto.constants.RSA_PKCS1_OAEP_PADDING},dataKey);
    return {id:String(r.id),alg:'RSA-OAEP-SHA256',wrappedKey:b64(key)};
  });
  dataKey.fill(0);
  return Object.freeze({schema:'deus.owner-vault-recovery/1',cipher:'AES-256-GCM',keyWrap:'RSA-OAEP-SHA256',context,iv:b64(iv),tag:b64(tag),ciphertext:b64(ciphertext),recipients:wrapped});
}

export function openRecoveryEnvelope({envelope,recipientId,privateKeyPem}={}){
  if(envelope?.schema!=='deus.owner-vault-recovery/1')throw new Error('INVALID_ENVELOPE');
  const item=envelope.recipients?.find(x=>x.id===recipientId);if(!item)throw new Error('RECIPIENT_NOT_FOUND');
  const dataKey=crypto.privateDecrypt({key:privateKeyPem,oaepHash:'sha256',padding:crypto.constants.RSA_PKCS1_OAEP_PADDING},unb64(item.wrappedKey));
  try{
    const decipher=crypto.createDecipheriv('aes-256-gcm',dataKey,unb64(envelope.iv));decipher.setAAD(Buffer.from(envelope.context));decipher.setAuthTag(unb64(envelope.tag));
    return Buffer.concat([decipher.update(unb64(envelope.ciphertext)),decipher.final()]).toString('utf8');
  } finally {dataKey.fill(0);}
}
