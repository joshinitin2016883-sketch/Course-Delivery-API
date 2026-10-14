import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";
import AuthProvider from "./components/AuthProvider";
import RequireAuth from "./components/RequireAuth";
import WakingBanner from "./components/WakingBanner";
import CourseListPage from "./pages/CourseListPage";
import CoursePage from "./pages/CoursePage";
import LoginPage from "./pages/LoginPage";
import MyCoursesPage from "./pages/MyCoursesPage";
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
            <Route path="/" element={<CourseListPage />} />
            <Route path="/courses/:courseId" element={<CoursePage />} />
            <Route path="/my-courses" element={<MyCoursesPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
