const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const path = require('node:path');
const source=fs.readFileSync(path.resolve(__dirname,'../src/fresh/preparation.ts'),'utf8');
const context={exports:{}};
vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,context);
const {preparation}=context.exports;
function fixture() {
  return {challenge:{id:'c',code:'SSH',victim_id:'v',strategy:'SSH',groups:['g'],pilot_passed:false,state:'draft'},
    machines:[{id:'v',name:'VICTIM',kind:'victima',state:'ready',busy:false},{id:'a',name:'KALI',kind:'atacante',state:'ready',busy:false}],
    labs:[{state:'ready',machines:['v']},{state:'ready',machines:['a']}],groups:[{id:'g',active_players:1}],scenarios:[{strategy:'SSH',victims:['VICTIM'],enabled:true}],runs:[]};
}
test('guardar un borrador completa creación, no piloto ni publicación',()=>{
  const r=preparation(fixture());assert.equal(r.steps[2].done,true);assert.equal(r.next.id,'pilot');assert.equal(r.canPilot,true);assert.equal(r.canPublish,false);assert.equal(r.complete,false);
});
test('una víctima ajena disponible no completa la preparación del reto elegido',()=>{
  const f=fixture();f.machines[0].state='dirty';f.machines.push({id:'other',name:'VICTIM',kind:'victima',state:'ready'});f.labs[0].machines.push('other');const r=preparation(f);assert.equal(r.steps[0].done,false);assert.equal(r.canPilot,false);
});
test('la Kali disponible necesita pertenecer a un laboratorio disponible',()=>{
  const f=fixture();f.labs[1].state='planned';assert.equal(preparation(f).steps[1].done,false);assert.equal(preparation(f).canPilot,false);
});
test('un grupo vacío o no asignado no satisface jugadores',()=>{
  const f=fixture();f.groups[0].active_players=0;f.groups.push({id:'unassigned',active_players:3});assert.equal(preparation(f).steps[4].done,false);f.groups[0].active_players=1;assert.equal(preparation(f).steps[4].done,true);
});
test('un piloto aún limpiando no se toma como aprobado ni se duplica',()=>{
  const f=fixture();f.runs=[{challenge_id:'c',pilot:true,state:'reiniciando'}];const r=preparation(f);assert.equal(r.steps[5].done,false);assert.equal(r.pilotRunning,true);assert.equal(r.canPilot,false);assert.equal(r.canPublish,false);f.challenge.pilot_passed=true;assert.equal(preparation(f).canPublish,false);
});
test('un escenario deshabilitado nunca completa el recorrido aunque esté publicado',()=>{
  const f=fixture();f.challenge.pilot_passed=true;f.challenge.state='published';f.scenarios[0].enabled=false;const r=preparation(f);assert.equal(r.complete,false);assert.equal(r.canPilot,false);assert.equal(r.canPublish,false);
});
test('publicación con requisitos satisfechos y regresión posterior por mantenimiento',()=>{
  const f=fixture();f.challenge.pilot_passed=true;assert.equal(preparation(f).canPublish,true);f.challenge.state='published';assert.equal(preparation(f).complete,true);f.machines[0].state='mantenimiento';const r=preparation(f);assert.equal(r.complete,false);assert.equal(r.steps[6].done,true);
});
test('ocupación implica cola, no pérdida de configuración',()=>{
  const f=fixture();f.challenge.pilot_passed=true;f.challenge.state='published';f.machines[0].busy=true;const r=preparation(f);assert.equal(r.complete,true);assert.equal(r.resourceBusy,true);
});
test('el recorrido nuevo no hereda creación ni piloto del reto anterior',()=>{
  const f=fixture();delete f.challenge;const r=preparation(f);assert.equal(r.steps[2].done,false);assert.equal(r.next.id,'draft');assert.equal(r.canPilot,false);assert.equal(r.canPublish,false);
});
