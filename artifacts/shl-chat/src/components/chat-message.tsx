import { BrainCircuit, User } from 'lucide-react';
import { Message } from '../hooks/use-chat';
import { RecommendationCard } from './recommendation-card';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  
  return (
    <div 
      className={cn(
        "flex w-full px-4 py-4 md:px-8 md:py-5 animate-in fade-in slide-in-from-bottom-2 duration-300",
        isUser ? "justify-end" : "justify-start"
      )}
      data-testid={`chat-message-${message.role}`}
    >
      <div className={cn(
        "flex gap-3 max-w-4xl w-full",
        isUser && "flex-row-reverse"
      )}>
        {/* Avatar */}
        <div className={cn(
          "shrink-0 w-9 h-9 rounded-xl flex items-center justify-center",
          isUser 
            ? "bg-[#dce9c8] text-[#3e5b35]" 
            : "bg-[#18352c] text-[#d7f06c] shadow-sm"
        )}>
          {isUser ? <User className="w-4 h-4" /> : <BrainCircuit className="w-4 h-4" />}
        </div>

        {/* Content Area */}
        <div className={cn(
          "flex flex-col gap-3 min-w-0 flex-1",
          isUser && "items-end"
        )}>
          {/* Text Bubble */}
          <div className={cn(
            "rounded-2xl px-4 py-3 text-sm leading-7 relative",
            isUser 
              ? "bg-[#e7eedf] text-[#263c33] rounded-tr-md" 
              : "bg-white/90 border border-[#e2e7df] text-[#35483f] rounded-tl-md shadow-[0_3px_14px_-10px_rgba(24,53,44,0.25)]",
            message.isError && "bg-red-50 text-red-700 border-red-200"
          )}>
            <div className="whitespace-pre-wrap wrap-break-word">
              {message.content}
            </div>
          </div>
          
          {/* Recommendations */}
          {message.recommendations && message.recommendations.length > 0 && (
            <div className="flex flex-col gap-2 mt-1 w-full">
              {message.recommendations.map((rec, i) => (
                <RecommendationCard key={i} recommendation={rec} index={i} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
