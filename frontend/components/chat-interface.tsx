"use client";

import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import {
  Sparkles,
  Plus,
  MessageCircle,
  Settings,
  Send,
  Mic,
  ShieldCheck,
  Wifi,
  WifiOff,
  LoaderCircle,
  Languages,
} from "lucide-react";

import {
  createConversation,
  getConversationSocketUrl,
} from "@/lib/api";

import type {
  ChatLanguage,
  ChatMessage,
  ServerEvent,
} from "@/lib/types";


type ConnectionStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "disconnected";


const quickPrompts = [
  "Let's have a conversation.",
  "Help me with my coding.",
  "Teach me some Japanese.",
];


export default function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const [conversationId, setConversationId] =
    useState<string | null>(null);

  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("idle");

  const [language, setLanguage] =
    useState<ChatLanguage>("auto");

  const [draft, setDraft] = useState("");

  const [waiting, setWaiting] = useState(false);

  const [error, setError] = useState<string | null>(null);


  const socketRef = useRef<WebSocket | null>(null);

  const busyRef = useRef(false);

  const bottomRef = useRef<HTMLDivElement | null>(null);


  // Keep the latest message visible.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, waiting]);


  // Close the WebSocket when the component unmounts.
  useEffect(() => {
    return () => {
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, []);


  // ----------------------------------
  // WebSocket connection
  // ----------------------------------

  function connectSocket(
    id: string
  ): Promise<WebSocket> {
    const existingSocket = socketRef.current;

    if (
      existingSocket &&
      existingSocket.readyState === WebSocket.OPEN
    ) {
      return Promise.resolve(existingSocket);
    }

    setConnectionStatus("connecting");

    return new Promise((resolve, reject) => {
      const socket = new WebSocket(
        getConversationSocketUrl(id)
      );

      socketRef.current = socket;

      let opened = false;

      const timeout = window.setTimeout(() => {
        if (!opened) {
          socket.close();
          reject(
            new Error("WebSocket connection timed out.")
          );
        }
      }, 10000);


      socket.onopen = () => {
        opened = true;

        window.clearTimeout(timeout);

        setConnectionStatus("connected");

        resolve(socket);
      };


      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(
            event.data
          ) as ServerEvent;


          if (
            data.type === "user_message_saved" ||
            data.type === "assistant_message"
          ) {
            setMessages((previous) => [
              ...previous,
              data.message,
            ]);

            if (data.type === "assistant_message") {
              setWaiting(false);
              busyRef.current = false;
            }
          }


          if (data.type === "error") {
            setError(data.message);

            setWaiting(false);

            busyRef.current = false;
          }

        } catch {
          setError("Could not read the server response.");

          setWaiting(false);

          busyRef.current = false;
        }
      };


      socket.onerror = () => {
        window.clearTimeout(timeout);

        setConnectionStatus("disconnected");

        if (!opened) {
          reject(
            new Error("Could not connect to Alya's backend.")
          );
        }
      };


      socket.onclose = () => {
        window.clearTimeout(timeout);

        if (socketRef.current === socket) {
          socketRef.current = null;

          setConnectionStatus("disconnected");

          setWaiting(false);

          busyRef.current = false;
        }

        if (!opened) {
          reject(
            new Error("WebSocket connection was closed.")
          );
        }
      };
    });
  }


  // ----------------------------------
  // Send a message
  // ----------------------------------

  async function handleSend(
    event?: FormEvent<HTMLFormElement>
  ) {
    event?.preventDefault();

    const content = draft.trim();

    if (!content || busyRef.current) {
      return;
    }

    busyRef.current = true;

    setDraft("");

    setWaiting(true);

    setError(null);


    try {
      let activeConversationId = conversationId;


      // Create a conversation when the first
      // message is sent.
      if (!activeConversationId) {
        const conversation = await createConversation();

        activeConversationId = conversation.id;

        setConversationId(conversation.id);
      }


      // Connect to the WebSocket.
      const socket = await connectSocket(
        activeConversationId
      );


      // Send the message to FastAPI.
      socket.send(
        JSON.stringify({
          type: "user_message",
          content,
          language,
        })
      );

    } catch (err) {
      busyRef.current = false;

      setWaiting(false);

      setDraft(content);

      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong."
      );
    }
  }


  // ----------------------------------
  // Start a new conversation
  // ----------------------------------

  function handleNewConversation() {
    const socket = socketRef.current;

    socketRef.current = null;

    socket?.close();

    setConversationId(null);

    setMessages([]);

    setWaiting(false);

    setError(null);

    setConnectionStatus("idle");

    busyRef.current = false;

    setDraft("");
  }


  // ----------------------------------
  // Keyboard interaction
  // ----------------------------------

  function handleKeyDown(
    event: KeyboardEvent<HTMLTextAreaElement>
  ) {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();

      void handleSend();
    }
  }


  function formatTime(date: string) {
    return new Date(date).toLocaleTimeString(
      [],
      {
        hour: "2-digit",
        minute: "2-digit",
      }
    );
  }


  const statusLabel = {
    idle: "Ready",
    connecting: "Connecting...",
    connected: "Connected",
    disconnected: "Disconnected",
  }[connectionStatus];


  return (
    <div className="app-shell">

      {/* SIDEBAR */}

      <aside className="sidebar">

        <div className="brand">
          <div className="brand-icon">
            <Sparkles size={23} />
          </div>

          <div>
            <h2>ALYA</h2>
            <span>PERSONAL COMPANION</span>
          </div>
        </div>


        <button
          className="new-chat-button"
          onClick={handleNewConversation}
        >
          <Plus size={18} />
          New conversation
        </button>


        <div className="sidebar-section">
          <span className="sidebar-label">
            YOUR COMPANION
          </span>

          <div className="companion-item">
            <div className="small-avatar">A</div>

            <div className="companion-info">
              <strong>Alya</strong>
              <span>Always here for you</span>
            </div>

            <span className="online-dot" />
          </div>
        </div>


        <div className="sidebar-note">
          <MessageCircle size={16} />

          <div>
            <strong>Current session</strong>
            <span>
              {messages.length} messages
            </span>
          </div>
        </div>


        <div className="sidebar-spacer" />


        <div className="privacy-card">
          <ShieldCheck size={20} />

          <div>
            <strong>Privacy first</strong>
            <span>Mac access not connected</span>
          </div>
        </div>


        <button
          className="settings-button"
          disabled
          title="Settings will be implemented later"
        >
          <Settings size={17} />
          Settings
        </button>

      </aside>


      {/* MAIN APPLICATION */}

      <main className="main-panel">

        {/* HEADER */}

        <header className="topbar">

          <div className="topbar-title">
            <span className="topbar-eyebrow">
              ALYA / COMPANION SPACE
            </span>

            <span className="topbar-subtitle">
              Your personal AI companion
            </span>
          </div>


          <div className="topbar-actions">

            <div
              className={`connection-status ${connectionStatus}`}
            >
              {connectionStatus === "connected" ? (
                <Wifi size={14} />
              ) : connectionStatus === "connecting" ? (
                <LoaderCircle size={14} className="spin" />
              ) : (
                <WifiOff size={14} />
              )}

              <span>{statusLabel}</span>
            </div>


            <div className="language-control">
              <Languages size={16} />

              <select
                value={language}
                onChange={(event) =>
                  setLanguage(
                    event.target.value as ChatLanguage
                  )
                }
                aria-label="Conversation language"
              >
                <option value="auto">
                  Auto
                </option>

                <option value="en">
                  English
                </option>

                <option value="zh">
                  中文
                </option>

                <option value="ja">
                  日本語
                </option>
              </select>
            </div>

          </div>

        </header>


        {/* CONVERSATION AREA */}

        <section className="conversation-area">

          {messages.length === 0 ? (

            <div className="welcome-screen">

              <div className="avatar-orbit">

                <div className="orbit-ring orbit-one" />

                <div className="orbit-ring orbit-two" />

                <div className="avatar-glow" />

                <div className="avatar-main">
                  A
                </div>

                <span className="avatar-sparkle">
                  ✦
                </span>

              </div>


              <div className="welcome-label">
                YOUR COMPANION IS HERE
              </div>


              <h1>
                Hey, I am <span>Alya.</span>
              </h1>


              <p className="welcome-description">
                I have been waiting for you.
                <br />
                What would you like to talk about today?
              </p>


              <div className="quick-prompts">

                {quickPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => setDraft(prompt)}
                  >
                    {prompt}
                  </button>
                ))}

              </div>

            </div>

          ) : (

            <div className="message-list">

              {messages.map((message) => (

                <div
                  key={message.id}
                  className={`message-row ${message.role}`}
                >

                  {message.role === "assistant" && (
                    <div className="message-avatar">
                      A
                    </div>
                  )}


                  <div className="message-stack">

                    <div className="message-author">

                      {message.role === "assistant"
                        ? "Alya"
                        : "You"}

                      {message.emotion && (
                        <span className="emotion-label">
                          {message.emotion}
                        </span>
                      )}

                    </div>


                    <div
                      className={`message-bubble ${message.role}`}
                    >
                      {message.content}
                    </div>


                    <span className="message-time">
                      {formatTime(message.created_at)}
                    </span>

                  </div>

                </div>

              ))}


              {waiting && (
                <div className="message-row assistant">

                  <div className="message-avatar">
                    A
                  </div>

                  <div className="message-stack">

                    <div className="message-author">
                      Alya
                    </div>

                    <div className="message-bubble typing">
                      <span />
                      <span />
                      <span />
                    </div>

                  </div>

                </div>
              )}


              <div ref={bottomRef} />

            </div>

          )}

        </section>


        {/* MESSAGE INPUT */}

        <footer className="composer-section">

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}


          <form
            className="message-composer"
            onSubmit={(event) => void handleSend(event)}
          >

            <textarea
              value={draft}
              onChange={(event) =>
                setDraft(event.target.value)
              }
              onKeyDown={handleKeyDown}
              placeholder="Message Alya..."
              rows={1}
              maxLength={4000}
            />


            <div className="composer-bottom">

              <div className="composer-hint">
                <span>↵</span>
                Send · Shift + Enter for new line
              </div>


              <div className="composer-actions">

                <button
                  type="button"
                  className="mic-button"
                  disabled
                  title="Voice input will be added in Phase 3"
                >
                  <Mic size={18} />
                </button>


                <button
                  type="submit"
                  className="send-button"
                  disabled={!draft.trim() || waiting}
                  aria-label="Send message"
                >
                  <Send size={18} />
                </button>

              </div>

            </div>

          </form>


          <div className="composer-disclaimer">
            Alya is currently running in development mode.
          </div>

        </footer>

      </main>

    </div>
  );
}