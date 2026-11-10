const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const path = require('node:path');
const source = fs.readFileSync(path.resolve(__dirname, '../src/fresh/client.ts'), 'utf8');
const compiled = ts.transpileModule(source, {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;

function clientFixture() {
  let saved = 'old-session';
  let respond;
  const events = [];
  const context = {exports:{}, Event, sessionStorage:{getItem:()=>saved,setItem:(_,value)=>{saved=value;},removeItem:()=>{saved=null;}},window:{dispatchEvent:event=>events.push(event.type)},fetch:()=>new Promise(resolve=>{respond=resolve;})};
  vm.runInNewContext(compiled, context);
  return {...context.exports, events, respond:(status,body)=>respond({ok:status<400,status,json:async()=>body})};
}

test('una respuesta tardía de la sesión anterior no cierra una sesión nueva', async () => {
  const fixture = clientFixture();
  const request = fixture.api('/machines');
  fixture.token.set('new-session');
  fixture.respond(401,{message:'Sesión vencida'});
  await assert.rejects(request,/Sesión vencida/);
  assert.equal(fixture.token.get(),'new-session');
  assert.deepEqual(fixture.events,[]);
});

test('una sesión actual vencida limpia el acceso y avisa a la interfaz', async () => {
  const fixture = clientFixture();
  const request = fixture.api('/machines');
  fixture.respond(401,{message:'Sesión vencida'});
  await assert.rejects(request);
  assert.equal(fixture.token.get(),null);
  assert.deepEqual(fixture.events,['fresh-logout']);
});

test('un login incorrecto conserva el error sin disparar un cierre de sesión', async () => {
  const fixture = clientFixture();
  const request = fixture.api('/auth/login',{username:'test',password:'synthetic'});
  fixture.respond(401,{message:'Credenciales incorrectas'});
  await assert.rejects(request,/Credenciales incorrectas/);
  assert.deepEqual(fixture.events,[]);
});
