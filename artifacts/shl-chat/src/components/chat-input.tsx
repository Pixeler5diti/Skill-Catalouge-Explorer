import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { ArrowUp } from 'lucide-react';
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
    <div className="relative flex w-full items-end gap-2 rounded-[22px] border border-[#dce3d8] bg-white p-2 shadow-[0_12px_35px_-24px_rgba(24,53,44,0.45)] transition-all focus-within:border-[#9eaf88] focus-within:shadow-[0_12px_36px_-20px_rgba(76,112,62,0.32)]">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Describe a role, skill, or hiring challenge…"
        className="flex-1 max-h-50 min-h-12 w-full resize-none bg-transparent px-4 py-3.5 text-sm text-[#30453b] placeholder:text-[#9aa69e] focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 scrollbar-hide"
        disabled={isLoading}
        rows={1}
        data-testid="message-input"
      />
      <button
        onClick={handleSend}
        disabled={!input.trim() || isLoading}
        aria-label="Send message"
        className={cn(
          "inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-[15px] transition-all",
          input.trim() && !isLoading
            ? "bg-[#18352c] text-[#d7f06c] hover:bg-[#294b3f] hover:shadow-md"
            : "bg-[#f0f3ed] text-[#a5afa8] cursor-not-allowed"
        )}
        data-testid="send-button"
      >
        <ArrowUp className="h-5 w-5" />
      </button>
    </div>
  );
}
