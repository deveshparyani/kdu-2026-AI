// Why this file exists:
// It renders server-defined widgets inline inside assistant messages.

import TravelOfferWidget from "./TravelOfferWidget";
import type { ChatMessage, TravelOfferWidget as TravelOfferWidgetType, UserId } from "../../lib/types";

type WidgetRendererProps = {
  widgets: TravelOfferWidgetType[];
  userId: UserId;
  threadId: string | null;
  onAssistantMessage: (message: ChatMessage) => void;
};

export default function WidgetRenderer({
  widgets,
  userId,
  threadId,
  onAssistantMessage
}: WidgetRendererProps) {
  if (widgets.length === 0 || threadId === null) {
    return null;
  }

  return (
    <section className="inline-widget-list">
      {widgets.map((widget) => (
        <TravelOfferWidget
          key={widget.widget_id}
          widget={widget}
          userId={userId}
          threadId={threadId}
          onAssistantMessage={onAssistantMessage}
        />
      ))}
    </section>
  );
}
