import { useEffect, useState } from "react";
import { setSlowRequestHandler } from "../api/client";

// The API's free server sleeps when idle, and its first answer can take up to a minute.
// The client tells this banner when any request has been running for over 3 seconds.
export default function WakingBanner() {
  const [waking, setWaking] = useState(false);

  useEffect(() => {
    setSlowRequestHandler(setWaking);
  }, []);

  // The status region is always present, so screen readers announce the message when it appears.
  return (
    <div role="status" className="pointer-events-none fixed inset-x-0 bottom-4 z-10 flex justify-center px-4">
      {waking && (
        <p className="rounded-lg bg-ink px-4 py-3 text-sm text-page shadow-md">
          Waking the server, this can take up to a minute…
        </p>
      )}
    </div>
  );
}
