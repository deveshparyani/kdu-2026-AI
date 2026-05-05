// Why this file exists:
// It is the main orchestrator for sessions, messages, widgets, and handoff controls.

import { useState } from "react";

import ChatKitMountPoint from "./ChatKitMountPoint";
import ChatWindow from "./ChatWindow";
import HumanHandoffPanel from "./HumanHandoffPanel";
import MessageInput from "./MessageInput";
import SessionBar from "./SessionBar";
import {
  createChatSession,
  streamChatMessage,
  type StreamEventHandler
} from "../lib/api";
import type { ChatMessage, ChatStreamEvent, SessionResult, UserId } from "../lib/types";

function buildLocalUserMessage(content: string): ChatMessage {
  return {
    id: `local_user_${Date.now()}`,
    role: "user",
    content,
    created_at: new Date().toISOString(),
    widgets: []
  };
}

function buildPendingAssistantMessage(): ChatMessage {
  return {
    id: `local_assistant_${Date.now()}`,
    role: "assistant",
    content: "",
    created_at: new Date().toISOString(),
    widgets: []
  };
}

export default function ChatApp() {
  const [selectedUser, setSelectedUser] = useState<UserId>("user_a");
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isResponding, setIsResponding] = useState(false);
  const [statusMessage, setStatusMessage] = useState(
    "Start a new chat or send a message to begin."
  );
  const [errorMessage, setErrorMessage] = useState("");

  function applySession(response: SessionResult) {
    setCurrentThreadId(response.thread_id);
    setClientSecret(response.client_secret);
    setMessages(response.messages);
    setStatusMessage(`Connected to thread ${response.thread_id}.`);
    setErrorMessage("");
  }

  async function handleCreateNewThread() {
    setStatusMessage("Creating a new secure chat thread...");
    setErrorMessage("");

    try {
      const response = await createChatSession({ userId: selectedUser });
      applySession(response);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Could not create a new chat."
      );
    }
  }

  async function handleContinueThread(threadId: string) {
    setStatusMessage("Trying to continue the selected thread...");
    setErrorMessage("");

    try {
      const response = await createChatSession({
        userId: selectedUser,
        threadId
      });
      applySession(response);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Could not continue this thread."
      );
    }
  }

  function handleUserSwitch(userId: UserId) {
    setSelectedUser(userId);
    setCurrentThreadId(null);
    setClientSecret(null);
    setMessages([]);
    setErrorMessage("");
    setStatusMessage("User changed. Start a new chat or continue a thread.");
  }

  function appendAssistantMessage(message: ChatMessage) {
    setMessages((currentMessages) => [...currentMessages, message]);
  }

  async function handleSendMessage(messageText: string) {
    const trimmedMessage = messageText.trim();
    if (!trimmedMessage || isResponding) {
      return;
    }

    let activeThreadId = currentThreadId;
    let activeClientSecret = clientSecret;

    if (activeThreadId === null) {
      try {
        const session = await createChatSession({ userId: selectedUser });
        applySession(session);
        activeThreadId = session.thread_id;
        activeClientSecret = session.client_secret;
      } catch (error) {
        setErrorMessage(
          error instanceof Error
            ? error.message
            : "Could not create a chat before sending the message."
        );
        return;
      }
    }

    const userMessage = buildLocalUserMessage(trimmedMessage);
    const pendingAssistantMessage = buildPendingAssistantMessage();

    setMessages((currentMessages) => [
      ...currentMessages,
      userMessage,
      pendingAssistantMessage
    ]);
    setIsResponding(true);
    setErrorMessage("");
    setStatusMessage("Assistant is responding...");
    setClientSecret(activeClientSecret);

    const handleStreamEvent: StreamEventHandler = (event: ChatStreamEvent) => {
      setMessages((currentMessages) =>
        currentMessages.map((message) => {
          if (message.id !== pendingAssistantMessage.id) {
            return message;
          }

          if (event.type === "assistant_delta") {
            return {
              ...message,
              content: `${message.content}${event.text}`
            };
          }

          if (event.type === "widget") {
            return {
              ...message,
              widgets: [...message.widgets, event.widget]
            };
          }

          return message;
        })
      );

      if (event.type === "done") {
        setIsResponding(false);
        setStatusMessage("Assistant response completed.");
      }
    };

    try {
      await streamChatMessage({
        userId: selectedUser,
        threadId: activeThreadId,
        message: trimmedMessage,
        onEvent: handleStreamEvent
      });
    } catch (error) {
      setMessages((currentMessages) =>
        currentMessages.filter((message) => message.id !== pendingAssistantMessage.id)
      );
      setIsResponding(false);
      setErrorMessage(
        error instanceof Error ? error.message : "The streaming request failed."
      );
      setStatusMessage("Assistant response failed.");
    }
  }

  return (
    <main className="chat-app-shell">
      <SessionBar
        selectedUser={selectedUser}
        onUserChange={handleUserSwitch}
        currentThreadId={currentThreadId}
        onCreateNewThread={handleCreateNewThread}
        onContinueThread={handleContinueThread}
      />

      {errorMessage ? (
        <section className="error-banner">
          <strong>Error:</strong> {errorMessage}
        </section>
      ) : null}

      <section className="chat-layout">
        <section className="chat-column">
          <ChatWindow
            messages={messages}
            selectedUser={selectedUser}
            currentThreadId={currentThreadId}
            onAssistantMessage={appendAssistantMessage}
            isResponding={isResponding}
            statusMessage={statusMessage}
          />
          <MessageInput
            onSendMessage={handleSendMessage}
            disabled={isResponding}
          />
        </section>

        <aside className="side-column">
          <HumanHandoffPanel
            selectedUser={selectedUser}
            threadId={currentThreadId}
          />
          <ChatKitMountPoint
            clientSecret={clientSecret}
            threadId={currentThreadId}
          />
        </aside>
      </section>
    </main>
  );
}
