import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { SendHorizontal } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading: boolean;
}

export function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    onSend(input);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="relative flex w-full max-w-3xl mx-auto items-end gap-2 bg-card border border-border/60 shadow-sm rounded-2xl p-2 focus-within:ring-1 focus-within:ring-primary/50 focus-within:border-primary/50 transition-all">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask for an assessment recommendation..."
        className="flex-1 max-h-[200px] min-h-[44px] w-full resize-none bg-transparent px-3 py-3 text-sm focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 scrollbar-hide"
        disabled={isLoading}
        rows={1}
        data-testid="message-input"
      />
      <button
        onClick={handleSend}
        disabled={!input.trim() || isLoading}
        className={cn(
          "inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl transition-colors",
          input.trim() && !isLoading
            ? "bg-primary text-primary-foreground hover:bg-primary/90"
            : "bg-muted text-muted-foreground cursor-not-allowed"
        )}
        data-testid="send-button"
      >
        <SendHorizontal className="h-5 w-5" />
      </button>
    </div>
  );
}
