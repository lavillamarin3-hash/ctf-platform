import type { Challenge, Group, Laboratory, Machine, Run, Scenario } from './client';

export type PreparationInput = { challenge?: Challenge; machines: Machine[]; labs: Laboratory[]; groups: Group[]; scenarios: Scenario[]; runs: Run[] };
export type PreparationStep = { id: string; label: string; done: boolean; detail: string; destination: string };

// Estado derivado: no hay casillas locales que puedan certificar una prueba remota.
export function preparation({challenge, machines, labs, groups, scenarios, runs}: PreparationInput) {
  const scenario = scenarios.find(s => s.strategy === challenge?.strategy);
  const victims = machines.filter(m => m.kind === 'victima' && (challenge ? m.id === challenge.victim_id && Boolean(scenario?.victims.includes(m.name)) : scenarios.some(s => s.victims.includes(m.name))));
  const attackers = machines.filter(m => m.kind === 'atacante');
  const readyVictims = victims.filter(m => m.state === 'ready');
  const readyAttackers = attackers.filter(m => m.state === 'ready');
  const inReadyLab = (m: Machine) => labs.some(l => l.state === 'ready' && l.machines.includes(m.id));
  const victimLabs = readyVictims.filter(inReadyLab);
  const attackerLabs = readyAttackers.filter(inReadyLab);
  const assigned = groups.filter(g => challenge?.groups?.includes(g.id));
  const audience = assigned.some(g => (g.active_players ?? 0) > 0);
  const pilot = runs.find(r => r.challenge_id === challenge?.id && r.pilot && ['en_cola','reservada','activa','reiniciando'].includes(r.state));
  const steps: PreparationStep[] = [
    {id:'machines',label:'Máquinas',done:readyVictims.length > 0 && readyAttackers.length > 0,detail:challenge ? 'La víctima de este reto y al menos una Kali deben estar confirmadas como disponibles.' : 'Confirma una víctima compatible y una Kali. Al crear el reto se revisará su víctima concreta.',destination:'maquinas'},
    {id:'labs',label:'Laboratorios',done:victimLabs.length > 0 && attackerLabs.length > 0,detail:'La víctima y una Kali disponibles deben pertenecer a laboratorios disponibles.',destination:'laboratorios'},
    {id:'draft',label:'Crear reto',done:Boolean(challenge),detail:challenge ? `${challenge.code}: creado correctamente.` : 'Define el escenario, la víctima, las instrucciones y las pistas; guarda el borrador.',destination:'create'},
    {id:'integration',label:'Integración',done:Boolean(scenario?.enabled),detail:!challenge ? 'Selecciona el escenario al crear el borrador.' : scenario?.enabled ? 'Integración habilitada. El piloto comprobará la preparación y la limpieza.' : 'El operador debe completar y validar la integración de este escenario. No puede publicarse todavía.',destination:'requirements'},
    {id:'groups',label:'Jugadores',done:audience,detail:audience ? 'Hay al menos un grupo asignado con jugadores activos.' : 'Crea un grupo con jugadores activos y asígnalo a este reto.',destination:'assignment'},
    {id:'pilot',label:'Piloto',done:Boolean(challenge?.pilot_passed),detail:pilot ? 'Hay un piloto en curso. Espera su resultado y la limpieza en Corridas.' : challenge?.pilot_passed ? 'La plataforma registró un piloto aprobado y su limpieza correcta.' : 'Ejecuta el piloto y espera que termine correctamente, incluida la limpieza.',destination:'pilot'},
    {id:'publish',label:'Publicar',done:challenge?.state === 'published',detail:challenge?.state === 'published' ? 'Reto publicado. Revisa también los requisitos actuales antes de otra práctica.' : 'Publica cuando los pasos anteriores estén completos.',destination:'publish'},
  ];
  const completed = steps.filter(s => s.done).length;
  const next = steps.find(s => !s.done);
  const resourceBusy = victimLabs.some(m => m.busy) || (attackerLabs.length > 0 && attackerLabs.every(m => m.busy));
  return {steps, completed, next, complete:completed === steps.length, pilotRunning:Boolean(pilot), resourceBusy,
    canPilot:Boolean(challenge && steps[0].done && steps[1].done && scenario?.enabled && !pilot),
    canPublish:!pilot && steps.slice(0,6).every(s => s.done) && challenge?.state !== 'published'};
}
