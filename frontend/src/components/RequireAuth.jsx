import { Navigate, Outlet } from "react-router";
import { useAuth } from "./AuthProvider";
import NavBar from "./NavBar";

// The layout for every signed-in page: the nav bar, then the page. Without a user, go to /login.
// This only decides what to show; the API refuses any request without a valid token anyway.
export default function RequireAuth() {
  const { user } = useAuth();

  if (user === null) {
    return <Navigate to="/login" replace />;
  }

  return (
    <>
      <NavBar />
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
    </>
  );
}
