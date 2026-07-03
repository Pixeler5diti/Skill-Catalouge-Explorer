import { useState, useCallback, useEffect } from 'react';

export type Role = 'user' | 'assistant';

export interface Recommendation {
  name: string;
  url: string;
  test_type: string;
}

export interface Message {
  role: Role;
  content: string;
  recommendations?: Recommendation[];
  isError?: boolean;
}

const BASE = import.meta.env.VITE_SHL_API_URL || "/shl-api";

console.log("==================================");
console.log("API BASE =", BASE);
console.log("==================================");

export function useChat() {
  console.log("useChat() hook mounted");

  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [health, setHealth] = useState<'ok' | 'error' | 'loading'>('loading');

  useEffect(() => {
    console.log("========== HEALTH CHECK ==========");
    console.log("Fetching:", `${BASE}/health`);

    let mounted = true;

    (async () => {
      try {
        const res = await fetch(`${BASE}/health`, {
          method: "GET",
          mode: "cors",
          cache: "no-store",
        });

        console.log("Response received");
        console.log("Status:", res.status);
        console.log("OK:", res.ok);

        const text = await res.text();
        console.log("Response body:", text);

        if (!mounted) return;

        try {
          const data = JSON.parse(text);

          if (data.status === "ok") {
            console.log("Backend healthy");
            setHealth("ok");
          } else {
            console.log("Unexpected health payload");
            setHealth("error");
          }
        } catch (err) {
          console.error("JSON parse failed:", err);
          setHealth("error");
        }
      } catch (err) {
        console.error("Health fetch FAILED:", err);
        if (mounted) setHealth("error");
      }
    })();

    return () => {
      mounted = false;
    };
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    const newMsg: Message = {
      role: "user",
      content,
    };

    setMessages(prev => [...prev, newMsg]);
    setIsLoading(true);

    try {
      const messagesToSend = messages
        .filter(m => !m.isError)
        .concat(newMsg)
        .map(m => ({
          role: m.role,
          content: m.content,
        }));

      console.log("POSTING TO:", `${BASE}/chat`);
      console.log("Payload:", messagesToSend);

      const res = await fetch(`${BASE}/chat`, {
        method: "POST",
        mode: "cors",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: messagesToSend,
        }),
      });

      console.log("Chat response status:", res.status);

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();

      console.log("Chat response:", data);

      setMessages(prev => [
        ...prev,
        {
          role: "assistant",
          content: data.reply,
          recommendations: data.recommendations,
        },
      ]);
    } catch (err) {
      console.error("Chat request failed:", err);

      setMessages(prev => [
        ...prev,
        {
          role: "assistant",
          content: "I encountered an error communicating with the server. Please try again.",
          isError: true,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [messages, isLoading]);

  const clearChat = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    isLoading,
    sendMessage,
    clearChat,
    health,
  };
}