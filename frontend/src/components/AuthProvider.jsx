import { createContext, useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router";
import * as authApi from "../api/auth";
import { clearToken, getToken, setToken, setUnauthorizedHandler } from "../api/client";
import { ErrorMessage, Loading } from "./States";

const AuthContext = createContext(null);

// Any component can call useAuth() for the signed-in user (or null), login and logout.
export function useAuth() {
  return useContext(AuthContext);
}

export default function AuthProvider({ children }) {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  // With a saved token, we ask the server who it belongs to before showing any page.
  const [checking, setChecking] = useState(() => getToken() !== null);
  const [checkError, setCheckError] = useState(null);

  // A 401 from any request means the token is no longer good. The client clears it and calls this.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      navigate("/login", { replace: true });
    });
  }, [navigate]);

  // The user and their role always come from GET /auth/me, never from reading the token.
  useEffect(() => {
    if (getToken() === null) {
      return;
    }
    authApi
      .getMe()
      .then(setUser)
      .catch((error) => {
        // A 401 has already signed us out. Anything else means the server couldn't be asked.
        if (error.status !== 401) {
          setCheckError(error.message);
        }
      })
      .finally(() => setChecking(false));
  }, []);

  // Returns the signed-in user, so the sign-in page can choose where they land.
  async function login(email, password) {
    const { access_token } = await authApi.login(email, password);
    setToken(access_token);
    const me = await authApi.getMe();
    setUser(me);
    return me;
  }

  function logout() {
    clearToken();
    setUser(null);
    navigate("/login", { replace: true });
  }

  if (checking) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Loading />
      </main>
    );
  }

  if (checkError) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-8">
        <ErrorMessage message={checkError} onRetry={() => window.location.reload()} />
      </main>
    );
  }

  return <AuthContext value={{ user, login, logout }}>{children}</AuthContext>;
}
