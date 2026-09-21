import test from 'node:test';
import assert from 'node:assert/strict';
import { GoogleSheetsCanonicalBridge } from '../bridge/drive-machine-bridge.mjs';

test('bridge verifies read and heartbeat append with fixed spreadsheet scope',async()=>{
  const calls=[];
  const fetchImpl=async (url,init={})=>{
    calls.push({url:String(url),method:init.method||'GET'});
    if(String(url).includes(':append')){
      return {ok:true,status:200,text:async()=>JSON.stringify({updates:{updatedRange:'54_MACHINE_BRIDGE_HEALTH!A2:H2',updatedRows:1}})};
    }
    return {ok:true,status:200,text:async()=>JSON.stringify({range:'10_LIGHT_BOOT!A2:O2',values:[['boot']]})};
  };
  const bridge=new GoogleSheetsCanonicalBridge({
    spreadsheetId:'sheet123',
    tokenSource:async()=> 'token',
    fetchImpl,
    instanceId:'test-instance',
    clock:()=>Date.parse('2026-09-21T00:00:00Z'),
  });
  const receipt=await bridge.verifyReadWrite({receiptRef:'RCP-X'});
  assert.equal(receipt.state,'LIVE');
  assert.equal(receipt.readRowCount,1);
  assert.equal(receipt.heartbeatUpdatedRange,'54_MACHINE_BRIDGE_HEALTH!A2:H2');
  assert.equal(calls.length,2);
  assert.match(calls[0].url,/sheet123/);
  assert.match(calls[1].url,/:append/);
});
