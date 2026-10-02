import type { Flag } from "../models/challenge";

export type FlagDraft = {
  id?: number;
  label: string;
  mode: "static" | "dynamic";
  value: string;
  template: string;
  flag_order: number;
  is_active: boolean;
};

/** Matches the existing editor default without generating or validating a flag. */
export function initialFlagTemplate(flag: Flag, challengeCode: string): string {
  return flag.template ?? `FLAG{${challengeCode}}-{{RUN_ID}}-{{RAND}}`;
}

/** Content-only challenge edits must leave its runtime flags untouched. */
export function hasFlagDraftChanges(existing: Flag | undefined, draft: FlagDraft, challengeCode: string): boolean {
  if (!existing) return true;
  if (
    existing.label.trim() !== draft.label.trim() ||
    (existing.mode ?? "static") !== draft.mode ||
    existing.flag_order !== draft.flag_order ||
    existing.is_active !== draft.is_active
  ) return true;
  if (draft.mode === "static") {
    // The API deliberately omits existing plaintext; empty means retain that value.
    return Boolean(draft.value.trim());
  }
  return initialFlagTemplate(existing, challengeCode).trim() !== draft.template.trim();
}
