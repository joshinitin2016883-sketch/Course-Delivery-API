import { useState } from "react";
import { Navigate, useNavigate } from "react-router";
import { useAuth } from "../components/AuthProvider";
import { ErrorMessage } from "../components/States";

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // Already signed in: there is nothing to do here.
  if (user !== null) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      // The server's own message, such as "Incorrect email or password."
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <p className="text-xs font-semibold tracking-wider text-muted uppercase">Course Delivery</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Sign in</h1>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4 rounded-xl border border-line bg-surface p-6">
          <div>
            <label htmlFor="email" className="block text-sm font-medium">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="input mt-1"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="input mt-1"
            />
          </div>
          {error && <ErrorMessage message={error} />}
          <button type="submit" disabled={submitting} className="btn-primary w-full">
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-sm text-muted">
          Demo accounts: learner@example.com (learner) and instructor@example.com (instructor). The
          password is in SUBMISSION.md.
        </p>
      </div>
    </main>
  );
}
