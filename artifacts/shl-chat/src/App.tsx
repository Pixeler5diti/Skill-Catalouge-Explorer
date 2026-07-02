import { useEffect, useRef } from 'react';
import { Route, Switch, Router as WouterRouter } from 'wouter';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PlusCircle, Search } from 'lucide-react';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import NotFound from '@/pages/not-found';

import { useChat } from './hooks/use-chat';
import { HealthStatus } from './components/health-status';
import { EmptyState } from './components/empty-state';
import { ChatMessage } from './components/chat-message';
import { ChatInput } from './components/chat-input';

const queryClient = new QueryClient();

function ChatPage() {
  const { messages, isLoading, sendMessage, clearChat, health } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="flex flex-col h-[100dvh] w-full bg-background overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-border/40 bg-card/50 backdrop-blur-md z-10">
        <div className="flex items-center justify-between px-4 md:px-6 h-14 max-w-5xl mx-auto w-full">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary text-primary-foreground shadow-sm">
              <Search className="w-4 h-4" />
            </div>
            <h1 className="font-semibold tracking-tight text-foreground hidden sm:block">
              SHL Advisor
            </h1>
          </div>
          
          <div className="flex items-center gap-4">
            <HealthStatus status={health} />
            <div className="w-px h-4 bg-border hidden sm:block" />
            <button
              onClick={clearChat}
              disabled={messages.length === 0}
              className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="new-conversation-button"
            >
              <PlusCircle className="w-4 h-4" />
              <span className="hidden sm:inline">New chat</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Chat Area */}
      <main className="flex-1 overflow-y-auto scroll-smooth">
        <div className="max-w-5xl mx-auto w-full h-full flex flex-col">
          {messages.length === 0 ? (
            <div className="flex-1 flex items-center justify-center pb-20">
              <EmptyState onSelectPrompt={sendMessage} />
            </div>
          ) : (
            <div className="flex-1 py-6 flex flex-col">
              {messages.map((message, i) => (
                <ChatMessage key={i} message={message} />
              ))}
              
              {/* Typing indicator */}
              {isLoading && (
                <div className="flex w-full px-4 py-6 md:px-6 justify-start bg-muted/30">
                  <div className="flex gap-4 max-w-3xl w-full">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ring-1 bg-white text-primary ring-border shadow-sm dark:bg-card">
                      <div className="flex gap-1">
                        <span className="w-1 h-1 bg-primary/60 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                        <span className="w-1 h-1 bg-primary/60 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                        <span className="w-1 h-1 bg-primary/60 rounded-full animate-bounce"></span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} className="h-4 flex-shrink-0" />
            </div>
          )}
        </div>
      </main>

      {/* Footer / Input Area */}
      <footer className="flex-shrink-0 bg-gradient-to-t from-background to-transparent pt-4 pb-6 px-4 md:px-6 relative z-10">
        <div className="max-w-3xl mx-auto w-full flex flex-col gap-2">
          <ChatInput onSend={sendMessage} isLoading={isLoading} />
          <p className="text-center text-xs text-muted-foreground/70">
            Recommendations are based on the SHL Assessment Catalog.
          </p>
        </div>
      </footer>
    </div>
  );
}

function Router() {
  return (
    <Switch>
      <Route path="/" component={ChatPage} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
