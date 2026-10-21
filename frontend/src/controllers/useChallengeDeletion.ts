import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { Challenge, ChallengeDeletionPreview, ChallengeDeletionResult } from "../models";
import { canPermanentlyDeleteChallenge } from "../lib/challengeDeletion";
import { ApiError } from "../services/api/client";

export function useChallengeDeletion(
  isAdmin: boolean,
  onDeleted: (result: ChallengeDeletionResult) => Promise<void>,
) {
  const [target, setTarget] = useState<Pick<Challenge, "code" | "name"> | null>(null);
  const [preview, setPreview] = useState<ChallengeDeletionPreview | null>(null);
  const [confirmation, setConfirmation] = useState("");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestVersion = useRef(0);
  const deleting = useRef(false);
  useEffect(() => () => { requestVersion.current += 1; }, []);

  const fetchPreview = async (code: string, preserveError = false) => {
    const version = ++requestVersion.current;
    setLoading(true);
    setPreview(null);
    if (!preserveError) setError(null);
    try {
      const impact = await api.challengeDeletionPreview(code);
      if (version === requestVersion.current) setPreview(impact);
    } catch (err) {
      if (version === requestVersion.current) {
        setError(err instanceof Error ? err.message : "No se pudo consultar el impacto de la eliminación.");
      }
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  };

  const open = (challenge: Pick<Challenge, "code" | "name">) => {
    if (!isAdmin || deleting.current) return;
    setTarget(challenge);
    setConfirmation("");
    void fetchPreview(challenge.code);
  };
  const close = () => {
    if (deleting.current) return;
    requestVersion.current += 1;
    setTarget(null);
    setPreview(null);
    setConfirmation("");
    setError(null);
    setLoading(false);
  };
  const canDelete = canPermanentlyDeleteChallenge({
    isAdmin, code: target?.code ?? "", confirmation, preview, loading, busy,
  });
  const refresh = async () => {
    if (isAdmin && target && !deleting.current) await fetchPreview(target.code);
  };
  const remove = async () => {
    if (!target || deleting.current || !canDelete) return;
    deleting.current = true;
    setBusy(true);
    setError(null);
    let result: ChallengeDeletionResult;
    try {
      result = await api.permanentlyDeleteChallenge(target.code, confirmation);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo eliminar el reto.");
      // Una corrida puede iniciarse después de la vista previa: el servidor
      // decide otra vez y la nueva vista muestra el bloqueo actual.
      if (err instanceof ApiError && err.status === 409) await fetchPreview(target.code, true);
      deleting.current = false;
      setBusy(false);
      return;
    }
    deleting.current = false;
    setBusy(false);
    close();
    // La eliminación ya terminó; un fallo al actualizar el panel no permite
    // repetirla ni se presenta como si la operación irreversible hubiera fallado.
    await onDeleted(result);
  };
  return { target, preview, confirmation, setConfirmation, loading, busy, error, canDelete, open, close, refresh, remove };
}

export type ChallengeDeletionController = ReturnType<typeof useChallengeDeletion>;
