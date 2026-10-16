import { useEffect,useState } from 'react';
import type { Run } from '../../api';
import { request } from '../../services/api/client';
import { LaboratoryRunWorkspace } from './LaboratoryRunWorkspace';

type Result={correct:boolean;challenge_completed:boolean;awarded_points:number;message:string};
export function SshPracticeWorkspace({run,onClose,onSubmit}:{run:Run;onClose:(id:number)=>Promise<void>;onSubmit:(code:string,value:string)=>Promise<Result>}) {
  const [info,setInfo]=useState<{target:string;username:string;wordlist:string[];note:string}|null>(null);
  const [error,setError]=useState('');
  const [attempt,setAttempt]=useState(0);
  useEffect(()=>{let alive=true;setError('');request<typeof info>(`/runs/${run.id}/ssh-practice`).then(data=>{if(alive)setInfo(data);}).catch(e=>{if(alive)setError(e.message);});return()=>{alive=false;};},[run.id,attempt]);
  return <>
    <section className="instruction-box"><h3>Fuerza bruta de credenciales · SSH</h3>
      {info && <><p>Objetivo: <strong>{info.target}</strong> · Usuario de práctica: <strong>{info.username}</strong></p><p>{info.note}</p>
        <p>Desde Kali identifica cómo probar los candidatos contra el servicio autorizado, comprueba la credencial encontrada y recupera la evidencia de la sesión. Las ayudas están en el panel de pistas y descuentan puntos.</p>
        <details><summary>Diccionario de candidatos del laboratorio</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{info.wordlist?.join('\n')}</pre></details>
      </>}
      {error && <><p role="alert">{error}</p><button className="secondary-action" onClick={()=>setAttempt(v=>v+1)}>Reintentar</button></>}
    </section>
    <LaboratoryRunWorkspace run={run} onClose={onClose} onSubmit={onSubmit}/>
  </>;
}
