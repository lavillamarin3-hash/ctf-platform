type PreparedFlagCandidate =
  | { kind: "ready"; value: string; joinedLineBreaks: boolean }
  | { kind: "empty" | "ambiguous" };

/** Limpia solo saltos de línea causados al copiar una única FLAG{...} de la terminal. */
export function prepareFlagCandidate(input: string): PreparedFlagCandidate {
  const text = input.trim();
  if (!text) return { kind: "empty" };

  // Solo se unen saltos visuales de un token completo; nunca se extrae una
  // coincidencia desde texto adicional ni se decide si la respuesta es válida.
  if (/^FLAG\{[^\s{}]+\}$/.test(text)) {
    return { kind: "ready", value: text, joinedLineBreaks: false };
  }
  if (/^FLAG\{[^\s{}]+(?:(?:\r\n|\r|\n)[^\s{}]+)+\}$/.test(text)) {
    const value = text.replace(/[\r\n]/g, "");
    return { kind: "ready", value, joinedLineBreaks: value !== text };
  }

  // No adivinar qué parte corresponde a la flag si llegó un prompt, salida extra
  // o varias flags. Otras respuestas de una sola línea se dejan intactas.
  if (text.includes("FLAG{") || /[\r\n]/.test(text)) return { kind: "ambiguous" };
  return { kind: "ready", value: text, joinedLineBreaks: false };
}
