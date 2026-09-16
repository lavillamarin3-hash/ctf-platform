// ============================================================
// ENTRY POINT DEL INSTRUCTOR
// ============================================================

import { createElement, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { User } from "../api";
import { Theme, ThemePreference } from "../config";
import { ManagementApp } from "./ManagementApp";

export function InstructorApp({
  user,
  onLogout,
  theme,
  onToggleTheme,
  themePreference,
  onThemePreferenceChange,
  onUserChange,
}: {
  user: User;
  onLogout: () => void;
  theme: Theme;
  onToggleTheme: () => void;
  themePreference: ThemePreference;
  onThemePreferenceChange: (value: ThemePreference) => void;
  onUserChange: (user: User) => void;
}) {
  return (
    <ManagementApp
      user={user}
      onLogout={onLogout}
      theme={theme}
      onToggleTheme={onToggleTheme}
      themePreference={themePreference}
      onThemePreferenceChange={onThemePreferenceChange}
      onUserChange={onUserChange}
      panelRole="instructor"
    />
  );
}
