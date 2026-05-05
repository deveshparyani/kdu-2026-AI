// Why this file exists:
// It gives beginners a small, secondary control for pausing and resuming AI.

import { useEffect, useState } from "react";

import { endHumanHandoff, getThreadMode, startHumanHandoff } from "../lib/api";
import type { ThreadMode, UserId } from "../lib/types";

type HumanHandoffPanelProps = {
  selectedUser: UserId;
  threadId: string | null;
};

export default function HumanHandoffPanel({
  selectedUser,
  threadId
}: HumanHandoffPanelProps) {
  const [mode, setMode] = useState<ThreadMode | null>(null);
  const [statusMessage, setStatusMessage] = useState(
    "Create or continue a thread to use handoff controls."
  );
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    async function loadMode() {
      if (threadId === null) {
        setMode(null);
        setStatusMessage("Create or continue a thread to use handoff controls.");
        return;
      }

      try {
        const response = await getThreadMode({ userId: selectedUser, threadId });
        setMode(response.mode);
        setStatusMessage("Thread mode loaded.");
      } catch (error) {
        setStatusMessage(
          error instanceof Error ? error.message : "Could not load thread mode."
        );
      }
    }

    void loadMode();
  }, [selectedUser, threadId]);

  async function handleStart() {
    if (threadId === null) {
      return;
    }

    setIsLoading(true);
    try {
      const response = await startHumanHandoff({ userId: selectedUser, threadId });
      setMode(response.mode);
      setStatusMessage(response.message);
    } catch (error) {
      setStatusMessage(
        error instanceof Error ? error.message : "Could not start handoff."
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function handleEnd() {
    if (threadId === null) {
      return;
    }

    setIsLoading(true);
    try {
      const response = await endHumanHandoff({ userId: selectedUser, threadId });
      setMode(response.mode);
      setStatusMessage(response.message);
    } catch (error) {
      setStatusMessage(
        error instanceof Error ? error.message : "Could not end handoff."
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="side-panel">
      <h3>Human Handoff</h3>
      <p className="subtle-text">
        When handoff is active, the user can still send messages, but the
        backend replies with an AI paused message instead of a normal AI answer.
      </p>

      <div className="mode-pill">
        Current mode: <code>{mode ?? "(unknown)"}</code>
      </div>

      {mode === "human" ? (
        <div className="mini-warning">
          AI is paused. A human agent can respond manually.
        </div>
      ) : null}

      <div className="side-panel-actions">
        <button
          className="secondary-button"
          type="button"
          onClick={handleStart}
          disabled={threadId === null || isLoading}
        >
          Start Human Handoff
        </button>
        <button
          className="secondary-button"
          type="button"
          onClick={handleEnd}
          disabled={threadId === null || isLoading}
        >
          End Human Handoff
        </button>
      </div>

      <p className="subtle-text">{statusMessage}</p>
    </section>
  );
}
