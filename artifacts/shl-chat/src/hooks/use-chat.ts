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

const BASE = import.meta.env.VITE_SHL_API_URL || '/shl-api';

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [health, setHealth] = useState<'ok' | 'error' | 'loading'>('loading');

  useEffect(() => {
    let mounted = true;
    
    fetch(`${BASE}/health`)
      .then(res => res.json())
      .then(data => {
        if (mounted) {
          if (data.status === 'ok') setHealth('ok');
          else setHealth('error');
        }
      })
      .catch(() => {
        if (mounted) setHealth('error');
      });
      
    return () => {
      mounted = false;
    };
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;
    
    const newMsg: Message = { role: 'user', content };
    setMessages(prev => [...prev, newMsg]);
    setIsLoading(true);

    try {
      const messagesToSend = messages
        .filter(m => !m.isError)
        .concat(newMsg)
        .map(m => ({
          role: m.role,
          content: m.content
        }));
      
      const res = await fetch(`${BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: messagesToSend })
      });

      if (!res.ok) throw new Error('Failed to fetch response');
      const data = await res.json();
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.reply,
        recommendations: data.recommendations
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'I encountered an error communicating with the server. Please try again.',
        isError: true
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [messages, isLoading]);

  const clearChat = useCallback(() => setMessages([]), []);

  return { messages, isLoading, sendMessage, clearChat, health };
}
