import { useEffect,useState } from 'react';
import type { Run } from '../../api';
import { request } from '../../services/api/client';
import { LaboratoryRunWorkspace } from './LaboratoryRunWorkspace';

type Result={correct:boolean;challenge_completed:boolean;awarded_points:number;message:string};
export function SshPracticeWorkspace({run,onClose,onSubmit}:{run:Run;onClose:(id:number)=>Promise<void>;onSubmit:(code:string,value:string)=>Promise<Result>}) {
  const [info,setInfo]=useState<{target:string;username:string;commands:string[];note:string}|null>(null);
  const [error,setError]=useState('');
  const [attempt,setAttempt]=useState(0);
  useEffect(()=>{let alive=true;setError('');request<typeof info>(`/runs/${run.id}/ssh-practice`).then(data=>{if(alive)setInfo(data);}).catch(e=>{if(alive)setError(e.message);});return()=>{alive=false;};},[run.id,attempt]);
  return <>
    <section className="instruction-box"><h3>Fuerza bruta de credenciales · SSH</h3>
      {info && <><p>Objetivo: <strong>{info.target}</strong> · Usuario de práctica: <strong>{info.username}</strong></p><p>{info.note}</p>
        <p>Ejecuta estos comandos en Kali, uno por uno. Hydra muestra la contraseña encontrada; úsala cuando SSH la solicite. Después copia la flag de <code>cat flag.txt</code> y envíala abajo.</p>
        {info.commands.map((command,index)=><div key={index} style={{margin:'0.75rem 0'}}><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{command}</pre>
          <button className="secondary-action" onClick={()=>void navigator.clipboard.writeText(command).catch(()=>setError('Copia el comando manualmente con Ctrl+C.'))}>Copiar paso {index+1}</button></div>)}
      </>}
      {error && <><p role="alert">{error}</p><button className="secondary-action" onClick={()=>setAttempt(v=>v+1)}>Reintentar</button></>}
    </section>
    <LaboratoryRunWorkspace run={run} onClose={onClose} onSubmit={onSubmit}/>
  </>;
}
