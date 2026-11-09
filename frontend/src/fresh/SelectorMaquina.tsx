import type { Machine } from './client';

export function SelectorMaquina({ machines, tipo, value, onChange, multiple = false }: { machines: Machine[]; tipo: 'atacante' | 'victima'; value: string | string[]; onChange: (value: string[]) => void; multiple?: boolean }) {
  return <select aria-label={tipo === 'atacante' ? 'Máquina atacante' : 'Máquina víctima'} required multiple={multiple} value={value} onChange={event => onChange(Array.from(event.target.selectedOptions, o => o.value))}>
    {!multiple && <option value="">Selecciona una máquina del inventario</option>}
    {machines.filter(vm => vm.kind === tipo).map(vm => <option key={vm.id} value={vm.id}>{vm.name} · {vm.ip} · {vm.state}</option>)}
  </select>;
}
