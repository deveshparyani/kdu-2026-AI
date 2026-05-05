// Why this file exists:
// It keeps session controls compact so the app feels like a real chat product.

import { useState } from "react";

import ThreadSecurityTester from "./ThreadSecurityTester";
import type { UserId } from "../lib/types";

type SessionBarProps = {
  selectedUser: UserId;
  onUserChange: (userId: UserId) => void;
  currentThreadId: string | null;
  onCreateNewThread: () => Promise<void>;
  onContinueThread: (threadId: string) => Promise<void>;
};

export default function SessionBar({
  selectedUser,
  onUserChange,
  currentThreadId,
  onCreateNewThread,
  onContinueThread
}: SessionBarProps) {
  const [showSecurityTester, setShowSecurityTester] = useState(false);

  return (
    <section className="session-bar">
      <div className="session-bar-main">
        <div>
          <p className="app-kicker">Secure Demo Chat</p>
          <h2>Travel Booking AI Agent</h2>
        </div>

        <div className="session-controls">
          <label className="compact-field">
            <span>User</span>
            <select
              value={selectedUser}
              onChange={(event) => onUserChange(event.target.value as UserId)}
            >
              <option value="user_a">user_a</option>
              <option value="user_b">user_b</option>
            </select>
          </label>

          <div className="thread-pill">
            <span>Thread</span>
            <code>{currentThreadId ?? "(none yet)"}</code>
          </div>

          <button className="primary-button" type="button" onClick={onCreateNewThread}>
            New Thread
          </button>

          <button
            className="secondary-button"
            type="button"
            onClick={() => setShowSecurityTester((currentValue) => !currentValue)}
          >
            {showSecurityTester ? "Hide Security Test" : "Security Test"}
          </button>
        </div>
      </div>

      {showSecurityTester ? (
        <ThreadSecurityTester
          selectedUser={selectedUser}
          onContinueThread={onContinueThread}
        />
      ) : null}
    </section>
  );
}
