// Why this file exists:
// It keeps the message composer focused and easy to reuse.

import { FormEvent, useState } from "react";

type MessageInputProps = {
  onSendMessage: (messageText: string) => Promise<void>;
  disabled: boolean;
};

export default function MessageInput({
  onSendMessage,
  disabled
}: MessageInputProps) {
  const [messageText, setMessageText] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedText = messageText.trim();
    if (!trimmedText || disabled) {
      return;
    }

    setMessageText("");
    await onSendMessage(trimmedText);
  }

  return (
    <form className="message-input-bar" onSubmit={handleSubmit}>
      <input
        aria-label="Travel message input"
        value={messageText}
        onChange={(event) => setMessageText(event.target.value)}
        placeholder="Ask for trips, flights, hotels, or budget options..."
        disabled={disabled}
      />
      <button className="primary-button" type="submit" disabled={disabled}>
        {disabled ? "Sending..." : "Send"}
      </button>
    </form>
  );
}
