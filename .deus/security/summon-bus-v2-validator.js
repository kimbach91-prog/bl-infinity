'use strict';

/**
 * Pure validation helpers for DEUS SUMMON_BUS V2.
 * No live Drive IDs or credentials belong in this public file.
 */

const REQUIRED_PACKET_FIELDS = Object.freeze([
  'BUS_VERSION',
  'TASK_ID',
  'NODE_ID',
  'TARGET',
  'DEDUPE_KEY',
  'REPLY_FOLDER_ID'
]);

const REQUIRED_RECEIPT_FIELDS = Object.freeze([
  'BUS_VERSION',
  'TASK_ID',
  'NODE_ID',
  'SOURCE_PACKET_FILE_ID',
  'SOURCE_PACKET_SHA256',
  'STATUS',
  'OBSERVED_AT',
  'CONSUMER_IDENTITY',
  'EVIDENCE_POINTER'
]);

function norm(value) {
  return String(value == null ? '' : value).trim();
}

function missingFields(object, fields) {
  return fields.filter((key) => !norm(object && object[key]));
}

function validatePacketV2(packet, expected) {
  const errors = [];
  const missing = missingFields(packet, REQUIRED_PACKET_FIELDS);
  if (missing.length) errors.push(`missing:${missing.join(',')}`);

  if (norm(packet.BUS_VERSION).toUpperCase() !== 'V2') errors.push('bus_version_not_v2');
  if (!/^V2[-_:]/.test(norm(packet.TASK_ID))) errors.push('task_id_not_v2_namespaced');
  if (!/^V2[-_:]/.test(norm(packet.DEDUPE_KEY))) errors.push('dedupe_key_not_v2_namespaced');

  if (expected) {
    if (expected.nodeId && norm(packet.NODE_ID).toUpperCase() !== norm(expected.nodeId).toUpperCase()) {
      errors.push('node_id_mismatch');
    }
    if (expected.nodeId && norm(packet.TARGET).toUpperCase() !== norm(expected.nodeId).toUpperCase()) {
      errors.push('target_mismatch');
    }
    if (expected.replyFolderId && norm(packet.REPLY_FOLDER_ID) !== norm(expected.replyFolderId)) {
      errors.push('reply_folder_mismatch');
    }
    if (expected.sourcePacketFileId && packet.SOURCE_PACKET_FILE_ID &&
        norm(packet.SOURCE_PACKET_FILE_ID) !== norm(expected.sourcePacketFileId)) {
      errors.push('source_packet_file_id_mismatch');
    }
    if (Array.isArray(expected.quarantinedFolderIds) &&
        expected.quarantinedFolderIds.map(norm).includes(norm(packet.REPLY_FOLDER_ID))) {
      errors.push('reply_folder_is_quarantined');
    }
  }

  return {ok: errors.length === 0, errors};
}

function validateReceiptV2(receipt, expected) {
  const errors = [];
  const missing = missingFields(receipt, REQUIRED_RECEIPT_FIELDS);
  if (missing.length) errors.push(`missing:${missing.join(',')}`);

  if (norm(receipt.BUS_VERSION).toUpperCase() !== 'V2') errors.push('bus_version_not_v2');
  if (!/^V2[-_:]/.test(norm(receipt.TASK_ID))) errors.push('task_id_not_v2_namespaced');
  if (!/^[a-f0-9]{64}$/i.test(norm(receipt.SOURCE_PACKET_SHA256))) errors.push('invalid_source_packet_sha256');

  if (expected) {
    if (expected.taskId && norm(receipt.TASK_ID) !== norm(expected.taskId)) errors.push('task_id_mismatch');
    if (expected.nodeId && norm(receipt.NODE_ID).toUpperCase() !== norm(expected.nodeId).toUpperCase()) {
      errors.push('node_id_mismatch');
    }
    if (expected.sourcePacketFileId && norm(receipt.SOURCE_PACKET_FILE_ID) !== norm(expected.sourcePacketFileId)) {
      errors.push('source_packet_file_id_mismatch');
    }
    if (expected.sourcePacketSha256 &&
        norm(receipt.SOURCE_PACKET_SHA256).toLowerCase() !== norm(expected.sourcePacketSha256).toLowerCase()) {
      errors.push('source_packet_hash_mismatch');
    }
    if (Array.isArray(expected.allowedStatuses) &&
        !expected.allowedStatuses.map((x) => norm(x).toUpperCase()).includes(norm(receipt.STATUS).toUpperCase())) {
      errors.push('status_not_allowed');
    }
  }

  return {ok: errors.length === 0, errors};
}

function canonicalStateFromEvidence({packetPresent, receiptValidation, executionEvidence}) {
  if (!packetPresent) return 'ABSENT';
  if (!receiptValidation || !receiptValidation.ok) return 'DISPATCHED';
  if (executionEvidence === true) return 'RETURNED';
  return 'READ';
}

module.exports = {
  REQUIRED_PACKET_FIELDS,
  REQUIRED_RECEIPT_FIELDS,
  validatePacketV2,
  validateReceiptV2,
  canonicalStateFromEvidence
};
