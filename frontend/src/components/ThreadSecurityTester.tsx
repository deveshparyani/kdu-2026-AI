// Why this file exists:
// It keeps the thread-isolation test available without making it the main UI.

import { useState } from "react";

import type { UserId } from "../lib/types";

type ThreadSecurityTesterProps = {
  selectedUser: UserId;
  onContinueThread: (threadId: string) => Promise<void>;
};

export default function ThreadSecurityTester({
  selectedUser,
  onContinueThread
}: ThreadSecurityTesterProps) {
  const [threadIdInput, setThreadIdInput] = useState("");

  return (
    <section className="security-tester-panel">
      <p className="subtle-text">
        This panel is only for thread ownership testing. The frontend sends
        `X-Demo-User-Id`, but the backend still validates that the pasted
        `thread_id` belongs to the current user.
      </p>
      <div className="security-tester-row">
        <input
          value={threadIdInput}
          onChange={(event) => setThreadIdInput(event.target.value)}
          placeholder={`Try a thread id as ${selectedUser}`}
        />
        <button
          className="secondary-button"
          type="button"
          onClick={() => onContinueThread(threadIdInput.trim())}
        >
          Continue Thread
        </button>
      </div>
    </section>
  );
}
