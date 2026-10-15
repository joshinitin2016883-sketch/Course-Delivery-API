import { createContext, useContext, useEffect, useState } from "react";
import { useLocation } from "react-router";
import { listAlerts } from "../api/alerts";
import { useAuth } from "./AuthProvider";

const AlertCountContext = createContext(null);

// The nav badge reads the count with useAlertCount(); the alerts page also sets it, after each dismiss.
export function useAlertCount() {
  return useContext(AlertCountContext);
}

// How many inactivity alerts there are, for instructors (null until known, and always for learners). It is
// asked for again on every move to another page, with no polling in between: alerts change slowly, over days.
export function AlertCountProvider({ children }) {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const [count, setCount] = useState(null);

  useEffect(() => {
    if (user.role !== "instructor") {
      return;
    }
    let ignore = false; // set when a newer load starts, so an older answer can't overwrite it
    listAlerts()
      .then((alerts) => {
        if (!ignore) {
          setCount(alerts.length);
        }
      })
      // The badge is a hint only: if it can't load, the nav simply shows no number.
      .catch(() => {});
    return () => {
      ignore = true;
    };
  }, [user, pathname]);

  return <AlertCountContext value={{ count, setCount }}>{children}</AlertCountContext>;
}
