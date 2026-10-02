import assert from "node:assert/strict";
import { test } from "node:test";
import { operationalLaboratories } from "../src/lib/operationalLabs.ts";

test("solo muestra las dos IP confirmadas sin borrar el inventario original", () => {
  const labs = [
    { id: "1", code: "LAB-ATACANTES", status: "Disponible", vms: [{ id: "1", name: "LAB-KALI", ip: "192.168.146.134", status: "ready" }, { id: "2", name: "LAB-KALI-PURPLE", ip: "10.10.20.11", status: "ready" }] },
    { id: "2", code: "LAB-VICTIMAS", status: "Disponible", vms: [{ id: "3", name: "LAB-LNXVICT", ip: "192.168.146.137", status: "ready" }, { id: "4", name: "LAB-SRVWEB", ip: "10.10.30.20", status: "ready" }, { id: "5", name: "LAB-KALI", ip: "192.168.146.134", status: "offline" }] },
    { id: "3", code: "LAB-01", status: "Disponible", vms: [] },
    { id: "4", code: "LAB-MANT", status: "Mantenimiento", vms: [{ id: "6", name: "LAB-LNXVICT", ip: "192.168.146.137", status: "ready" }] },
    { id: "5", code: "LAB-01-LEGACY", status: "Disponible", vms: [{ id: "7", name: "lab02", ip: "192.168.146.137", status: "ready" }] },
  ];
  const shown = operationalLaboratories(labs, new Map([["LAB-KALI", "192.168.146.134"], ["LAB-LNXVICT", "192.168.146.137"]]));
  assert.deepEqual(shown.map((lab) => [lab.code, lab.vms.map((vm) => vm.ip)]), [
    ["LAB-ATACANTES", ["192.168.146.134"]],
    ["LAB-VICTIMAS", ["192.168.146.137"]],
  ]);
  assert.equal(labs[0].vms.length, 2);
  assert.equal(labs[1].vms.length, 3);
  assert.equal(labs[2].vms.length, 0);
  assert.equal(labs[3].vms.length, 1);
  assert.equal(labs[4].vms.length, 1);
});
