import type { Laboratory } from "../config";

/** Vista reversible: filtra la presentación, nunca modifica el inventario del API. */
export function operationalLaboratories(laboratories: Laboratory[], targets: ReadonlyMap<string, string>): Laboratory[] {
  return laboratories
    .filter((lab) => lab.status === "Disponible")
    .map((lab) => ({ ...lab, vms: lab.vms.filter((vm) => vm.status === "ready" && targets.get(vm.name.toUpperCase()) === vm.ip) }))
    .filter((lab) => lab.vms.length > 0);
}
