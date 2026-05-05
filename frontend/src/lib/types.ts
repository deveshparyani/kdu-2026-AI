// Why this file exists:
// It stores the shared frontend types used by the chat UI and backend API helpers.

export type UserId = "user_a" | "user_b";
export type ThreadMode = "ai" | "human";

export type TravelOfferActionPayload = {
  offer_id: string;
};

export type TravelOfferAction = {
  type: "book_now";
  label: string;
  payload: TravelOfferActionPayload;
};

export type TravelOfferWidget = {
  type: "travel_offer";
  widget_id: string;
  title: string;
  destination: string;
  price: string;
  description: string;
  actions: TravelOfferAction[];
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  widgets: TravelOfferWidget[];
};

export type SessionStartRequest = {
  userId: UserId;
  threadId?: string;
};

export type SessionResult = {
  client_secret: string;
  thread_id: string;
  user_id: string;
  mode: ThreadMode;
  messages: ChatMessage[];
};

export type SendChatMessageRequest = {
  userId: UserId;
  threadId: string;
  message: string;
};

export type ChatResponse = {
  thread_id: string;
  mode: ThreadMode;
  assistant_message: ChatMessage;
};

export type ChatStreamEvent =
  | {
      type: "assistant_delta";
      text: string;
    }
  | {
      type: "widget";
      widget: TravelOfferWidget;
    }
  | {
      type: "done";
    };

export type ChatActionRequest = {
  userId: UserId;
  threadId: string;
  widgetId: string;
  actionType: "book_now";
  payload: TravelOfferActionPayload;
  idempotencyKey: string;
};

export type ChatActionResult = {
  status: "success";
  message: string;
  assistant_message: ChatMessage;
};

export type ThreadModeResult = {
  mode: ThreadMode;
};

export type ThreadHandoffResult = {
  mode: ThreadMode;
  message: string;
};
