// Why this file exists:
// It renders the conversation area of the chatbot.

import MessageBubble from "./MessageBubble";
import type { ChatMessage, UserId } from "../lib/types";

type ChatWindowProps = {
  messages: ChatMessage[];
  selectedUser: UserId;
  currentThreadId: string | null;
  onAssistantMessage: (message: ChatMessage) => void;
  isResponding: boolean;
  statusMessage: string;
};

export default function ChatWindow({
  messages,
  selectedUser,
  currentThreadId,
  onAssistantMessage,
  isResponding,
  statusMessage
}: ChatWindowProps) {
  return (
    <section className="chat-window">
      <header className="chat-window-header">
        <div>
          <h1>Travel Booking AI Agent</h1>
          <p className="subtle-text">
            Ask about destinations, budgets, weekend trips, flights, or hotels.
          </p>
        </div>
        <div className="chat-status-pill">{statusMessage}</div>
      </header>

      <div className="messages-scroll-area">
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            selectedUser={selectedUser}
            threadId={currentThreadId}
            onAssistantMessage={onAssistantMessage}
          />
        ))}

        {messages.length === 0 ? (
          <div className="empty-chat-state">
            Start a new chat and ask something like:
            <code>Find me a weekend trip to Goa under 10000</code>
          </div>
        ) : null}

        {isResponding ? (
          <div className="typing-indicator">Assistant is typing...</div>
        ) : null}
      </div>
    </section>
  );
}
