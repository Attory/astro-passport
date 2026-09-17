// SPDX-License-Identifier: AGPL-3.0-only
// Independent BigInt implementation; no Python process or shared runtime implementation.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
const profile = 'apt.sun-moon-content.v1-proposed';

function scaled(text, kind) {
  const m = /^(-?)([0-9]{1,3})(?:\.([0-9]{1,18}))?$/.exec(text);
  if (!m) throw Error('decimal');
  const [places,low,high] = {latitude:[7,-90,90],longitude:[7,-180,180],angle:[9,0,360]}[kind];
  const fraction=m[3]??'', denominator=10n**BigInt(fraction.length);
  const magnitude=BigInt(m[2]+fraction), sign=m[1]==='-'?-1n:1n;
  const signed=magnitude*sign;
  if (signed<BigInt(low)*denominator || signed>BigInt(high)*denominator || (kind==='angle'&&signed===360n*denominator)) throw Error('range');
  const numerator=magnitude*10n**BigInt(places);
  let quotient=numerator/denominator;
  const remainder=numerator%denominator;
  if(remainder*2n>denominator || (remainder*2n===denominator && quotient%2n===1n)) quotient++;
  let result=quotient*sign;
  if(kind==='angle') result%=360000000000n;
  if(kind==='longitude'&&result===1800000000n) result=-1800000000n;
  return Number(result);
}

function timestamp(value) {
  const m=/^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,6}))?Z$/.exec(value);
  if(!m) throw Error('utc');
  const [y,mo,d,h,mi,s]=m.slice(1,7).map(Number);
  const t=new Date(Date.UTC(y,mo-1,d,h,mi,s));
  if(t.getUTCFullYear()!==y || t.getUTCMonth()!==mo-1 || t.getUTCDate()!==d || t.getUTCHours()!==h || t.getUTCMinutes()!==mi || t.getUTCSeconds()!==s || t<new Date('1899-12-31T00:00:00Z') || t>=new Date('2101-01-02T00:00:00Z')) throw Error('utc range');
  return value.slice(0,19)+'.'+(m[7]??'').padEnd(6,'0')+'Z';
}

function canonical(value) {
  function normalize(v) {
    if(typeof v==='string') {
      if(!v.isWellFormed()) throw Error('surrogate');
      return v.normalize('NFC');
    }
    if(v===null || typeof v==='boolean') return v;
    if(typeof v==='number') { if(!Number.isSafeInteger(v)) throw Error('integer'); return Object.is(v,-0)?0:v; }
    if(Array.isArray(v)) return v.map(normalize);
    if(typeof v==='object') {
      const out=Object.create(null);
      for(const k of Object.keys(v)) { const n=normalize(k); if(Object.hasOwn(out,n)) throw Error('collision'); out[n]=normalize(v[k]); }
      // Serialize keys explicitly: JS object enumeration would reorder integer-like keys.
      return out;
    }
    throw Error('type');
  }
  function emit(v) {
    if(Array.isArray(v)) return '['+v.map(emit).join(',')+']';
    if(v!==null && typeof v==='object') return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+emit(v[k])).join(',')+'}';
    return JSON.stringify(v);
  }
  return Buffer.from(emit(normalize(value)),'utf8');
}

function evaluate(c) {
  try {
    const value=c.operation==='scale'?scaled(c.input,c.kind):c.operation==='timestamp'?timestamp(c.input):c.operation==='canonical'?c.input:(()=>{throw Error('op');})();
    const bytes=canonical(['ACEP1',profile,value]);
    return {value,utf8_hex:bytes.toString('hex'),sha256:createHash('sha256').update(bytes).digest('hex')};
  } catch {return {error:'invalid_canonical_input'};}
}
const vectors=JSON.parse(readFileSync(new URL('./vectors.json',import.meta.url),'utf8'));
for(const c of vectors.cases) {
  if(JSON.stringify(evaluate(c))!==JSON.stringify(c.expected)) {
    // Object insertion order in the returned diagnostic value is not semantic; bytes/digest are.
    const a=evaluate(c), b=c.expected;
    if(a.utf8_hex!==b.utf8_hex || a.sha256!==b.sha256 || a.error!==b.error) throw Error('vector '+c.id);
  }
}
console.log(`Independent Node conformance: ${vectors.cases.length} vectors passed`);
