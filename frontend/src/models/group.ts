/** Estudiante miembro de un grupo. */
export type GroupMember = {
  user_id: number;
  username: string;
  email: string | null;
  is_active: boolean;
};

/** Reto asignado a un grupo. */
export type GroupChallenge = {
  challenge_id: number;
  code: string;
  name: string;
};

/** Grupo académico y sus relaciones de acceso. */
export type StudentGroup = {
  id: number;
  name: string;
  code: string;
  description: string;
  is_active: boolean;
  guacamole_group_identifier?: string | null;
  members: GroupMember[];
  challenges: GroupChallenge[];
};
