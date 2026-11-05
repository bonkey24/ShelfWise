import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api, {
  getAccessToken,
  setTokens,
  clearAuth,
  setUser as storeUser,
  type UserProfile,
} from '../api/client';

interface AuthContextType {
  /** Current authenticated user, or null. */
  user: UserProfile | null;
  /** True while the initial token check / /auth/me/ call is in-flight. */
  loading: boolean;
  /** Log in with email + password. Throws on failure. */
  login: (email: string, password: string) => Promise<void>;
  /** Register a new account. Throws on failure. */
  register: (email: string, password: string, name?: string) => Promise<void>;
  /** Clear tokens and redirect to /login. */
  logout: () => void;
  /** Manually set the user (e.g. after SSO callback). */
  setUser: (user: UserProfile) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUserState] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  // On mount: if a token exists, fetch the current user profile.
  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get<UserProfile>('/auth/me/')
      .then((res) => {
        setUserState(res.data);
        storeUser(res.data);
      })
      .catch(() => {
        // Token expired / invalid – clear it silently.
        clearAuth();
        setUserState(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<{ access: string; refresh: string; user: UserProfile }>(
      '/auth/login/',
      { email, password },
    );
    const { access, refresh, user: u } = res.data;
    setTokens(access, refresh);
    storeUser(u);
    setUserState(u);
  }, []);

  const register = useCallback(async (email: string, password: string, name?: string) => {
    const res = await api.post<{ access: string; refresh: string; user: UserProfile }>(
      '/auth/register/',
      { email, password, ...(name ? { name } : {}) },
    );
    const { access, refresh, user: u } = res.data;
    setTokens(access, refresh);
    storeUser(u);
    setUserState(u);
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    setUserState(null);
    window.location.href = '/login';
  }, []);

  const setUser = useCallback((u: UserProfile) => {
    storeUser(u);
    setUserState(u);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
};

/** Hook to consume the auth context. Must be inside <AuthProvider>. */
export const useAuth = (): AuthContextType => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
};

export default AuthContext;

