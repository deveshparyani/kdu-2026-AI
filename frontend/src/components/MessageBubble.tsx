// Why this file exists:
// It renders one chat message and any inline widgets attached to it.

import WidgetRenderer from "./widgets/WidgetRenderer";
import type { ChatMessage, UserId } from "../lib/types";

type MessageBubbleProps = {
  message: ChatMessage;
  selectedUser: UserId;
  threadId: string | null;
  onAssistantMessage: (message: ChatMessage) => void;
};

export default function MessageBubble({
  message,
  selectedUser,
  threadId,
  onAssistantMessage
}: MessageBubbleProps) {
  const bubbleClassName =
    message.role === "user" ? "message-bubble user-bubble" : "message-bubble assistant-bubble";

  return (
    <article className={`message-row ${message.role === "user" ? "user-row" : "assistant-row"}`}>
      <div className={bubbleClassName}>
        <p className="message-role-label">
          {message.role === "user" ? "You" : "Assistant"}
        </p>
        <p className="message-text">{message.content || " "}</p>
        <WidgetRenderer
          widgets={message.widgets}
          userId={selectedUser}
          threadId={threadId}
          onAssistantMessage={onAssistantMessage}
        />
      </div>
    </article>
  );
}
