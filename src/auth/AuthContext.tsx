import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  ApiError,
  getCustomer,
  loginCustomer,
  logoutCustomer,
  refreshCsrfToken,
  registerCustomer,
  type CustomerAccount,
  type LoginRequest,
  type RegisterRequest,
} from "../lib/api";

type AuthContextValue = {
  customer: CustomerAccount | null;
  loading: boolean;
  error: string;
  login: (payload: LoginRequest) => Promise<CustomerAccount>;
  register: (payload: RegisterRequest) => Promise<CustomerAccount>;
  logout: () => Promise<void>;
  refresh: () => Promise<CustomerAccount | null>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [customer, setCustomer] = useState<CustomerAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const current = await getCustomer();
      await refreshCsrfToken();
      setCustomer(current);
      setError("");
      return current;
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        setCustomer(null);
        setError("");
        return null;
      }
      const message =
        requestError instanceof Error
          ? requestError.message
          : "Could not check your account session.";
      setError(message);
      throw requestError;
    }
  }, []);

  useEffect(() => {
    let active = true;
    getCustomer()
      .then(async (current) => {
        await refreshCsrfToken();
        if (active) {
          setCustomer(current);
          setError("");
        }
      })
      .catch((requestError: unknown) => {
        if (!active) return;
        if (requestError instanceof ApiError && requestError.status === 401) {
          setCustomer(null);
          return;
        }
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Could not check your account session.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (payload: LoginRequest) => {
    const current = await loginCustomer(payload);
    setCustomer(current);
    setError("");
    return current;
  }, []);

  const register = useCallback(async (payload: RegisterRequest) => {
    const current = await registerCustomer(payload);
    setCustomer(current);
    setError("");
    return current;
  }, []);

  const logout = useCallback(async () => {
    await logoutCustomer();
    setCustomer(null);
    setError("");
  }, []);

  const value = useMemo(
    () => ({ customer, loading, error, login, register, logout, refresh }),
    [customer, loading, error, login, register, logout, refresh],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider.");
  return context;
}
