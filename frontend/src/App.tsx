// Why this file exists:
// It keeps the top-level app small by delegating the full chat experience to ChatApp.

import ChatApp from "./components/ChatApp";

export default function App() {
  return <ChatApp />;
}
