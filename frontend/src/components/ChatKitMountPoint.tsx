// Why this file exists:
// It marks the exact place where an official ChatKit React UI could replace the custom chat window later.

type ChatKitMountPointProps = {
  clientSecret: string | null;
  threadId: string | null;
};

export default function ChatKitMountPoint({
  clientSecret,
  threadId
}: ChatKitMountPointProps) {
  // TODO:
  // If the official ChatKit React component is added to the project later,
  // mount it here and pass the backend-issued client secret plus the thread id.
  //
  // This custom chat UI already follows the same architecture:
  // - the browser gets a client secret from the backend
  // - the browser never sees the OpenAI API key
  // - the backend owns session creation, thread validation, widgets, and actions
  //
  // For now we return null so this placeholder does not dominate the real chat UI.
  void clientSecret;
  void threadId;
  return null;
}
