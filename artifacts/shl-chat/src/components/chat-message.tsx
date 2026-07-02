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
        "flex w-full px-4 py-6 md:px-6 animate-in fade-in slide-in-from-bottom-2 duration-300",
        isUser ? "justify-end" : "justify-start bg-muted/30"
      )}
      data-testid={`chat-message-${message.role}`}
    >
      <div className={cn(
        "flex gap-4 max-w-3xl w-full",
        isUser && "flex-row-reverse"
      )}>
        {/* Avatar */}
        <div className={cn(
          "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ring-1",
          isUser 
            ? "bg-primary text-primary-foreground ring-primary/20" 
            : "bg-white text-primary ring-border shadow-sm dark:bg-card"
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
            "rounded-2xl px-4 py-3 text-[15px] leading-relaxed relative",
            isUser 
              ? "bg-primary text-primary-foreground rounded-tr-sm" 
              : "bg-white border border-border/50 text-foreground rounded-tl-sm shadow-sm dark:bg-card",
            message.isError && "bg-destructive/10 text-destructive border-destructive/20"
          )}>
            <div className="whitespace-pre-wrap break-words">
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
