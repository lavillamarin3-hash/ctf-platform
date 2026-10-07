import assert from "node:assert/strict";
import { test } from "node:test";
import { prepareFlagCandidate } from "../src/lib/prepareFlagCandidate.ts";

test("conserva una flag de una línea", () => {
  assert.deepEqual(prepareFlagCandidate("  FLAG{ejemplo_123}  "), {
    kind: "ready", value: "FLAG{ejemplo_123}", joinedLineBreaks: false,
  });
});

test("conserva como candidato una flag con sufijo fuera de las llaves", () => {
  assert.deepEqual(prepareFlagCandidate("FLAG{esc-01}-208-abc123"), {
    kind: "ready", value: "FLAG{esc-01}-208-abc123", joinedLineBreaks: false,
  });
  assert.deepEqual(prepareFlagCandidate("prefijo-FLAG{ejemplo}"), {
    kind: "ready", value: "prefijo-FLAG{ejemplo}", joinedLineBreaks: false,
  });
});

test("une únicamente saltos CR y LF dentro de una flag copiada", () => {
  assert.deepEqual(prepareFlagCandidate("FLAG{ejem\r\nplo_\n123\r456}"), {
    kind: "ready", value: "FLAG{ejemplo_123456}", joinedLineBreaks: true,
  });
});

test("une un sufijo partido al copiar una sola flag", () => {
  assert.deepEqual(prepareFlagCandidate("FLAG{esc-01}-208-ab\r\nc123"), {
    kind: "ready", value: "FLAG{esc-01}-208-abc123", joinedLineBreaks: true,
  });
  assert.deepEqual(prepareFlagCandidate("FLAG{esc-01}\n-208-abc123"), {
    kind: "ready", value: "FLAG{esc-01}-208-abc123", joinedLineBreaks: true,
  });
});

test("rechaza prompt o salida adicional alrededor de la flag", () => {
  assert.deepEqual(prepareFlagCandidate("usuario@vm:~$ cat flag.txt"), { kind: "ambiguous" });
  assert.deepEqual(prepareFlagCandidate("usuario@vm:~$ cat flag.txt\nFLAG{ejemplo_123}"), { kind: "ambiguous" });
  assert.deepEqual(prepareFlagCandidate("FLAG{ejemplo_123}-208-ab\nusuario@vm:~$"), { kind: "ambiguous" });
  assert.deepEqual(prepareFlagCandidate("cwd=/home/usuario;FLAG{ejemplo_123}"), { kind: "ambiguous" });
  assert.deepEqual(prepareFlagCandidate("FLAG{ejemplo_123}\nfin"), { kind: "ambiguous" });
  assert.deepEqual(prepareFlagCandidate("FLAG{ejem\nplo}\nfin"), { kind: "ambiguous" });
  assert.deepEqual(prepareFlagCandidate("FLAG{ejemplo\n\n_123}"), { kind: "ambiguous" });
});

test("rechaza varias flags en una misma selección", () => {
  assert.deepEqual(prepareFlagCandidate("FLAG{primera}\nFLAG{segunda}"), { kind: "ambiguous" });
  assert.deepEqual(prepareFlagCandidate("FLAG{primera} FLAG{segunda}"), { kind: "ambiguous" });
});

test("preserva otras respuestas de una sola línea y rechaza texto multilinea", () => {
  assert.deepEqual(prepareFlagCandidate("  respuesta_estatica  "), {
    kind: "ready", value: "respuesta_estatica", joinedLineBreaks: false,
  });
  assert.deepEqual(prepareFlagCandidate("nota uno\nnota dos"), { kind: "ambiguous" });
  assert.deepEqual(prepareFlagCandidate("   "), { kind: "empty" });
});
