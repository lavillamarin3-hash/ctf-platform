/** Datos de usuario utilizados por autenticación y administración. */
export type User = {
  id: number;
  username: string;
  email: string | null;
  role: "admin" | "instructor" | "player" | "guest";
  is_active: boolean;
  full_name?: string | null;
  organization?: string | null;
  user_function?: string | null;
};
