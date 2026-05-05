// Why this file exists:
// It keeps backend request logic in one place so UI components stay readable.

import type {
  ChatActionRequest,
  ChatActionResult,
  ChatStreamEvent,
  SessionResult,
  SessionStartRequest,
  ThreadHandoffResult,
  ThreadModeResult,
  UserId
} from "./types";

const API_BASE_URL = "http://localhost:8000";
type ErrorPayload = { detail?: string };
export type StreamEventHandler = (event: ChatStreamEvent) => void;

export async function createChatSession({
  userId,
  threadId
}: SessionStartRequest): Promise<SessionResult> {
  const response = await fetch(`${API_BASE_URL}/api/chat/session`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      // Security choice:
      // the browser sends only the demo user header. It never sends the OpenAI
      // API key, and the backend still validates thread ownership separately.
      "X-Demo-User-Id": userId
    },
    body: JSON.stringify({
      ...(threadId ? { thread_id: threadId } : {})
    })
  });

  return handleApiResponse<SessionResult>(response);
}

export async function streamChatMessage({
  userId,
  threadId,
  message,
  onEvent
}: {
  userId: UserId;
  threadId: string;
  message: string;
  onEvent: StreamEventHandler;
}): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Demo-User-Id": userId
    },
    body: JSON.stringify({
      thread_id: threadId,
      message
    })
  });

  if (!response.ok) {
    const payload = await readJsonSafely(response);
    const detail =
      isErrorPayload(payload) && typeof payload.detail === "string"
        ? payload.detail
        : `Request failed with status ${response.status}.`;

    if (response.status === 403) {
      throw new Error(`403 Access denied: ${detail}`);
    }

    throw new Error(detail);
  }

  if (!response.body) {
    throw new Error("Streaming response body is missing.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let pendingText = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    pendingText += decoder.decode(value, { stream: true });
    const eventBlocks = pendingText.split("\n\n");
    pendingText = eventBlocks.pop() ?? "";

    for (const block of eventBlocks) {
      const dataLine = block
        .split("\n")
        .find((line) => line.startsWith("data: "));

      if (!dataLine) {
        continue;
      }

      const rawJson = dataLine.slice("data: ".length);
      const event = JSON.parse(rawJson) as ChatStreamEvent;
      onEvent(event);
    }
  }
}

export async function sendHiddenWidgetAction({
  userId,
  threadId,
  widgetId,
  actionType,
  payload,
  idempotencyKey
}: ChatActionRequest): Promise<ChatActionResult> {
  const response = await fetch(`${API_BASE_URL}/api/chat/action`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Demo-User-Id": userId
    },
    body: JSON.stringify({
      thread_id: threadId,
      widget_id: widgetId,
      action_type: actionType,
      payload,
      idempotency_key: idempotencyKey
    })
  });

  return handleApiResponse<ChatActionResult>(response);
}

export async function getThreadMode({
  userId,
  threadId
}: {
  userId: UserId;
  threadId: string;
}): Promise<ThreadModeResult> {
  const response = await fetch(`${API_BASE_URL}/api/threads/${threadId}/mode`, {
    headers: {
      "X-Demo-User-Id": userId
    }
  });

  return handleApiResponse<ThreadModeResult>(response);
}

export async function startHumanHandoff({
  userId,
  threadId
}: {
  userId: UserId;
  threadId: string;
}): Promise<ThreadHandoffResult> {
  const response = await fetch(
    `${API_BASE_URL}/api/threads/${threadId}/handoff/start`,
    {
      method: "POST",
      headers: {
        "X-Demo-User-Id": userId
      }
    }
  );

  return handleApiResponse<ThreadHandoffResult>(response);
}

export async function endHumanHandoff({
  userId,
  threadId
}: {
  userId: UserId;
  threadId: string;
}): Promise<ThreadHandoffResult> {
  const response = await fetch(
    `${API_BASE_URL}/api/threads/${threadId}/handoff/end`,
    {
      method: "POST",
      headers: {
        "X-Demo-User-Id": userId
      }
    }
  );

  return handleApiResponse<ThreadHandoffResult>(response);
}

async function handleApiResponse<T>(response: Response): Promise<T> {
  const payload = await readJsonSafely(response);

  if (!response.ok) {
    const detail =
      isErrorPayload(payload) && typeof payload.detail === "string"
        ? payload.detail
        : `Request failed with status ${response.status}.`;

    if (response.status === 403) {
      throw new Error(`403 Access denied: ${detail}`);
    }

    throw new Error(detail);
  }

  return payload as T;
}

async function readJsonSafely(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

function isErrorPayload(payload: unknown): payload is ErrorPayload {
  return typeof payload === "object" && payload !== null && "detail" in payload;
}
