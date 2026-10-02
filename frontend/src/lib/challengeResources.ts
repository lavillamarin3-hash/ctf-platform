export type ChallengeResource = {
  kind: "video" | "presentation";
  title: string;
  url: string;
};

const BLOCK_START = "[CTF_RESOURCES]";
const BLOCK_END = "[/CTF_RESOURCES]";
export const MAX_CHALLENGE_RESOURCES = 12;

/** Only web URLs without embedded credentials, or paths served by this platform. */
export function safeResourceUrl(value: string): string | null {
  const candidate = value.trim();
  if (!candidate || /[\u0000-\u0020\\]/.test(candidate)) return null;
  try {
    const url = new URL(candidate, "https://ctf.invalid");
    if (url.username || url.password) return null;
    if (candidate.startsWith("/") && !candidate.startsWith("//")) return candidate;
    return url.protocol === "https:" && candidate.startsWith("https://") ? url.href : null;
  } catch {
    return null;
  }
}

export function parseChallengeResources(instructions: string): {
  instructions: string;
  resources: ChallengeResource[];
} {
  // A marker mentioned inside a title or URL must not become a block boundary.
  const markers = [...instructions.matchAll(/^\[CTF_RESOURCES\][\t ]*\r?$/gm)];
  const start = markers.at(-1)?.index ?? -1;
  const end = instructions.lastIndexOf(BLOCK_END);
  if (start < 0 || end < start || instructions.slice(end + BLOCK_END.length).trim()) {
    return { instructions, resources: [] };
  }
  try {
    const raw: unknown = JSON.parse(instructions.slice(start + BLOCK_START.length, end));
    if (!Array.isArray(raw) || raw.length > MAX_CHALLENGE_RESOURCES) {
      return { instructions, resources: [] };
    }
    const resources: ChallengeResource[] = [];
    for (const item of raw) {
      if (!item || typeof item !== "object") return { instructions, resources: [] };
      const resource = item as Record<string, unknown>;
      if (
        (resource.kind !== "video" && resource.kind !== "presentation") ||
        typeof resource.title !== "string" ||
        typeof resource.url !== "string" ||
        !resource.title.trim() ||
        !safeResourceUrl(resource.url)
      ) return { instructions, resources: [] };
      resources.push({
        kind: resource.kind,
        title: resource.title.trim(),
        url: safeResourceUrl(resource.url)!,
      });
    }
    return { instructions: instructions.slice(0, start).trimEnd(), resources };
  } catch {
    // Keep old or malformed instructor content intact instead of silently deleting it.
    return { instructions, resources: [] };
  }
}

/** Stores optional learning material in the existing instructions field. No schema changes. */
export function serializeChallengeResources(
  instructions: string,
  resources: ChallengeResource[],
): string {
  if (resources.length > MAX_CHALLENGE_RESOURCES) throw new Error("Puedes añadir hasta 12 recursos por reto.");
  const normalized = resources.map((resource) => {
    const url = safeResourceUrl(resource.url);
    if (!resource.title.trim() || !url || (resource.kind !== "video" && resource.kind !== "presentation")) {
      throw new Error("Cada recurso necesita un título y una URL HTTPS o una ruta de la plataforma (/media/…).");
    }
    return { kind: resource.kind, title: resource.title.trim(), url };
  });
  const text = instructions.trim();
  return normalized.length ? `${text}\n\n${BLOCK_START}\n${JSON.stringify(normalized)}\n${BLOCK_END}` : text;
}

/** Embeds only validated public YouTube IDs. Other providers are offered as links. */
export function youtubeEmbedUrl(value: string): string | null {
  const safe = safeResourceUrl(value);
  if (!safe || safe.startsWith("/")) return null;
  const url = new URL(safe);
  let id: string | null = null;
  if (url.hostname === "youtu.be") id = url.pathname.slice(1);
  if (["youtube.com", "www.youtube.com", "m.youtube.com", "www.youtube-nocookie.com"].includes(url.hostname)) {
    if (url.pathname === "/watch") id = url.searchParams.get("v");
    if (url.pathname.startsWith("/embed/")) id = url.pathname.slice(7);
    if (url.pathname.startsWith("/shorts/")) id = url.pathname.slice(8);
  }
  return id && /^[A-Za-z0-9_-]{11}$/.test(id) ? `https://www.youtube-nocookie.com/embed/${id}` : null;
}
