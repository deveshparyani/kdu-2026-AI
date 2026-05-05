// Why this file exists:
// It renders one travel offer card inline inside the chat and sends a hidden action when booked.

import { useState } from "react";

import { sendHiddenWidgetAction } from "../../lib/api";
import type {
  ChatMessage,
  TravelOfferWidget as TravelOfferWidgetType,
  UserId
} from "../../lib/types";

type TravelOfferWidgetProps = {
  widget: TravelOfferWidgetType;
  userId: UserId;
  threadId: string;
  onAssistantMessage: (message: ChatMessage) => void;
};

export default function TravelOfferWidget({
  widget,
  userId,
  threadId,
  onAssistantMessage
}: TravelOfferWidgetProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [hasCompletedAction, setHasCompletedAction] = useState(false);

  const bookNowAction = widget.actions.find((action) => action.type === "book_now");

  async function handleBookNow() {
    if (bookNowAction === undefined || isSubmitting || hasCompletedAction) {
      return;
    }

    // Security choice:
    // the frontend sends the thread id because the backend must validate it.
    // The frontend never sends the OpenAI API key, and it never decides thread
    // ownership on its own.
    const idempotencyKey =
      typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `idemp_${Date.now()}_${Math.random().toString(36).slice(2)}`;

    setIsSubmitting(true);
    setErrorMessage("");

    try {
      const response = await sendHiddenWidgetAction({
        userId,
        threadId,
        widgetId: widget.widget_id,
        actionType: bookNowAction.type,
        payload: bookNowAction.payload,
        idempotencyKey
      });

      setHasCompletedAction(true);
      onAssistantMessage(response.assistant_message);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Could not start the booking flow."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <article className="travel-widget-card">
      <h4>{widget.title}</h4>
      <p className="widget-meta">Destination: {widget.destination}</p>
      <p className="widget-meta">Price: {widget.price}</p>
      <p>{widget.description}</p>
      <button
        className="primary-button"
        type="button"
        disabled={isSubmitting || hasCompletedAction}
        onClick={handleBookNow}
      >
        {isSubmitting ? "Booking..." : hasCompletedAction ? "Booked" : "Book Now"}
      </button>
      {errorMessage ? <p className="inline-error-text">{errorMessage}</p> : null}
    </article>
  );
}
