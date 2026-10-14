import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";
import AuthProvider from "./components/AuthProvider";
import RequireAuth from "./components/RequireAuth";
import WakingBanner from "./components/WakingBanner";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import "./index.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      {/* Outside AuthProvider, so it also shows while the first sign-in check waits for the server. */}
      <WakingBanner />
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          {/* Every other page needs a signed-in user. */}
          <Route element={<RequireAuth />}>
            <Route path="/" element={<p className="text-muted">The course list arrives in the next step.</p>} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
