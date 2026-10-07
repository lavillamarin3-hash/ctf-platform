type PreparedFlagCandidate =
  | { kind: "ready"; value: string; joinedLineBreaks: boolean }
  | { kind: "empty" | "ambiguous" };

/** Prepara texto copiado de la terminal; solo el backend valida la respuesta. */
export function prepareFlagCandidate(input: string): PreparedFlagCandidate {
  const text = input.trim();
  if (!text) return { kind: "empty" };

  const markers = text.match(/FLAG\{/g)?.length ?? 0;
  const hasControl = /[\x00-\x08\x09\x0B\x0C\x0E-\x1F\x7F]/.test(text);
  const hasPrompt = /(?:^|\s)[^\s]*[$#>]\s+\S/.test(text) ||
    /(?:^|[\r\n])\S+@\S+:[^\s]*[$#](?:\s|$)/.test(text);
  const leadingContext = markers === 1 ? text.slice(0, text.indexOf("FLAG{")) : "";
  if (hasControl || hasPrompt || markers > 1 || /[\s;:=]/.test(leadingContext)) {
    return { kind: "ambiguous" };
  }

  // Una línea es un candidato opaco: su formato y valor los decide el backend.
  if (!/[\r\n]/.test(text)) return { kind: "ready", value: text, joinedLineBreaks: false };

  // En varias líneas solo se unen fragmentos contiguos de un mismo token. La
  // comprobación de forma evita concatenar prompts, notas u otra flag copiada.
  const parts = text.split(/\r\n|\r|\n/);
  if (markers !== 1 || !parts[0].startsWith("FLAG{") ||
      parts.some((part, index) => !part || /\s/.test(part) ||
        (index < parts.length - 1 && part.endsWith("}") && !/^[-_]/.test(parts[index + 1])))) {
    return { kind: "ambiguous" };
  }
  return { kind: "ready", value: parts.join(""), joinedLineBreaks: true };
}
