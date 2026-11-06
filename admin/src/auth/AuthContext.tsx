import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, isUnauthenticated } from "../services/api";
import type { StaffAccount } from "../types";

type AuthValue = {
  staff: StaffAccount | null;
  loading: boolean;
  refresh: () => Promise<void>;
  login: (payload: { email: string; password: string; totp_code: string }) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [staff, setStaff] = useState<StaffAccount | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setStaff(await api.restore());
    } catch (error) {
      if (isUnauthenticated(error)) {
        setStaff(null);
        return;
      }
      throw error;
    }
  }, []);

  useEffect(() => {
    let active = true;
    api.restore()
      .then((account) => { if (active) setStaff(account); })
      .catch((error: unknown) => {
        if (active && isUnauthenticated(error)) setStaff(null);
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const login = useCallback(async (payload: { email: string; password: string; totp_code: string }) => {
    setStaff(await api.login(payload));
  }, []);
  const logout = useCallback(async () => {
    await api.logout();
    setStaff(null);
  }, []);
  const value = useMemo(() => ({ staff, loading, refresh, login, logout }), [
    staff, loading, refresh, login, logout,
  ]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider.");
  return value;
}
