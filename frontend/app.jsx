const { useState } = React;

function App() {
  const [apiBase, setApiBase] = useState("http://localhost:8080");
  const [sessionId, setSessionId] = useState("demo-session");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState([]);

  async function sendMessage(chatMessage) {
    const response = await fetch(`${apiBase.replace(/\/$/, "")}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sessionId: sessionId.trim() || "demo-session",
        message: chatMessage,
      }),
    });

    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }

    return response.json();
  }

  async function onSubmit(event) {
    event.preventDefault();
    const text = message.trim();
    if (!text || busy) return;

    setMessage("");
    setBusy(true);
    setMessages((prev) => [...prev, `You: ${text}`]);

    try {
      const data = await sendMessage(text);
      setMessages((prev) => [...prev, `Bot: ${data.reply || "(no reply)"}`]);
    } catch (error) {
      setMessages((prev) => [...prev, `Error: ${error.message}`]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <h1>CareCompass Prototype</h1>
      <p>Simple working client demo.</p>

      <label>
        Backend URL
        <input
          type="url"
          value={apiBase}
          onChange={(event) => setApiBase(event.target.value)}
        />
      </label>

      <label>
        Session ID
        <input
          type="text"
          value={sessionId}
          onChange={(event) => setSessionId(event.target.value)}
        />
      </label>

      <form onSubmit={onSubmit}>
        <input
          type="text"
          placeholder="Type a message"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          disabled={busy}
          required
        />
        <button type="submit" disabled={busy}>
          {busy ? "Sending..." : "Send"}
        </button>
      </form>

      <ul>
        {messages.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
