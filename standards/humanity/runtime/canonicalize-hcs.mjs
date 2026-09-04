import crypto from 'node:crypto';

function assertValidUnicodeString(value) {
  for (let i = 0; i < value.length; i += 1) {
    const code = value.charCodeAt(i);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(i + 1);
      if (!(next >= 0xdc00 && next <= 0xdfff)) throw new Error('HCS_JCS_INVALID_UNICODE');
      i += 1;
    } else if (code >= 0xdc00 && code <= 0xdfff) {
      throw new Error('HCS_JCS_INVALID_UNICODE');
    }
  }
  return value;
}

function assertPrimitive(value) {
  if (typeof value === 'string') return assertValidUnicodeString(value);
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error('HCS_JCS_NON_FINITE_NUMBER');
    return value;
  }
  if (value === null || typeof value === 'boolean') return value;
  if (value === undefined) throw new Error('HCS_JCS_UNDEFINED_FORBIDDEN');
  if (typeof value === 'bigint') throw new Error('HCS_JCS_BIGINT_FORBIDDEN_USE_STRING');
  return value;
}

// RFC 8785 JCS reference implementation for already-parsed I-JSON values.
// Duplicate property names MUST be rejected by the JSON parser before this function;
// a JavaScript object cannot retain duplicate keys after parsing.
export function canonicalizeHcs(value) {
  let output = '';

  const serialize = (input) => {
    const v = assertPrimitive(input);

    if (v === null || typeof v === 'boolean' || typeof v === 'number' || typeof v === 'string') {
      output += JSON.stringify(v);
      return;
    }

    if (Array.isArray(v)) {
      output += '[';
      for (let i = 0; i < v.length; i += 1) {
        if (i) output += ',';
        serialize(v[i]);
      }
      output += ']';
      return;
    }

    if (v && typeof v === 'object') {
      output += '{';
      const keys = Object.keys(v);
      for (const key of keys) assertValidUnicodeString(key);
      keys.sort(); // RFC 8785 sorting follows UTF-16 code unit order used by ECMAScript.
      keys.forEach((key, index) => {
        if (index) output += ',';
        output += JSON.stringify(key);
        output += ':';
        serialize(v[key]);
      });
      output += '}';
      return;
    }

    throw new Error(`HCS_JCS_UNSUPPORTED_TYPE:${typeof v}`);
  };

  serialize(value);
  return output;
}

export function canonicalBytesHcs(value) {
  return Buffer.from(canonicalizeHcs(value), 'utf8');
}

export function sha256Hcs(value) {
  return crypto.createHash('sha256').update(canonicalBytesHcs(value)).digest('hex');
}

export const HCS_CANONICALIZATION_PROFILE = 'urn:hcs:canonicalization:rfc8785-jcs';
