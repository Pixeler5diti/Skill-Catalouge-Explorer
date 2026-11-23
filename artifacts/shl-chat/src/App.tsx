import { useEffect, useRef } from 'react';
import { Route, Switch, Router as WouterRouter } from 'wouter';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Compass, Layers3, Plus, Sparkles } from 'lucide-react';
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
    <div className="flex h-dvh w-full overflow-hidden bg-[#f5f6f2] text-[#172a25]">
      <aside className="hidden w-[260px] shrink-0 flex-col justify-between bg-[#142c26] px-5 py-6 text-white md:flex">
        <div>
          <div className="flex items-center gap-3 px-1">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#d7f06c] text-[#19372e] shadow-lg shadow-black/10">
              <Compass className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[15px] font-bold tracking-tight">SHL Atlas</p>
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-white/45">Talent intelligence</p>
            </div>
          </div>

          <button
            onClick={clearChat}
            className="mt-10 flex w-full items-center justify-between rounded-xl border border-white/10 bg-white/[0.06] px-3.5 py-3 text-left text-sm font-medium text-white/90 transition hover:border-white/20 hover:bg-white/10"
            data-testid="new-conversation-button"
          >
            <span className="flex items-center gap-2.5"><Plus className="h-4 w-4 text-[#d7f06c]" /> New exploration</span>
            <span className="text-xs text-white/35">↵</span>
          </button>

          <div className="mt-10">
            <p className="px-2 text-[10px] font-bold uppercase tracking-[0.2em] text-white/35">Your workspace</p>
            <div className="mt-3 space-y-1">
              <div className="flex items-center gap-3 rounded-xl bg-white/[0.09] px-3 py-2.5 text-sm font-medium text-white">
                <Sparkles className="h-4 w-4 text-[#d7f06c]" /> Assessment finder
              </div>
              <div className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-white/55">
                <Layers3 className="h-4 w-4" /> Compare & shortlist
              </div>
            </div>
          </div>

          <div className="mt-10 rounded-2xl border border-white/10 bg-gradient-to-br from-white/[0.09] to-white/[0.02] p-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#d7f06c]"><span className="h-1.5 w-1.5 rounded-full bg-[#d7f06c]" /> Built for better decisions</div>
            <p className="mt-3 text-sm leading-6 text-white/65">Explore assessments by role, skill, duration, or capability.</p>
            <div className="mt-4 flex flex-wrap gap-1.5">
              {['Role fit', 'Skills', 'Duration'].map((tag) => <span key={tag} className="rounded-full border border-white/10 px-2.5 py-1 text-[10px] text-white/50">{tag}</span>)}
            </div>
          </div>
        </div>

        <div className="border-t border-white/10 pt-4">
          <div className="flex items-center justify-between"><span className="text-xs text-white/45">Catalog connection</span><HealthStatus status={health} /></div>
          <p className="mt-2 text-[10px] leading-4 text-white/30">Recommendations sourced from the SHL assessment catalog.</p>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="z-10 flex h-[68px] shrink-0 items-center justify-between border-b border-[#172a25]/[0.07] bg-[#f5f6f2]/90 px-4 backdrop-blur-xl md:px-9">
          <div className="flex items-center gap-3 md:hidden">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#142c26] text-[#d7f06c]"><Compass className="h-4 w-4" /></div>
            <span className="text-sm font-bold tracking-tight">SHL Atlas</span>
          </div>
          <div className="hidden items-center gap-2 text-xs text-[#728079] md:flex"><span>Workspace</span><span className="text-[#b8c0bb]">/</span><span className="font-semibold text-[#263b34]">Assessment finder</span></div>
          <div className="ml-auto flex items-center gap-3">
            <div className="md:hidden"><HealthStatus status={health} /></div>
            {messages.length > 0 && <button onClick={clearChat} className="inline-flex items-center gap-2 rounded-full border border-[#172a25]/10 bg-white px-3.5 py-2 text-xs font-semibold text-[#3d5149] shadow-sm transition hover:border-[#172a25]/20 hover:bg-[#fbfcf9]" data-testid="new-conversation-mobile"><Plus className="h-3.5 w-3.5" /> New</button>}
            <div className="hidden items-center gap-2 rounded-full border border-[#172a25]/10 bg-white px-3 py-2 md:flex"><span className="h-2 w-2 rounded-full bg-emerald-500" /><span className="text-xs font-medium text-[#52645c]">Assessment intelligence</span></div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto scroll-smooth">
          <div className="mx-auto flex min-h-full w-full max-w-6xl flex-col px-0 md:px-6">
          {messages.length === 0 ? (
            <div className="flex flex-1 items-center justify-center px-4 py-10 md:px-8 md:py-12">
              <EmptyState onSelectPrompt={sendMessage} />
            </div>
          ) : (
            <div className="flex flex-1 flex-col py-5 md:py-8">
              {messages.map((message, i) => (
                <ChatMessage key={i} message={message} />
              ))}
              
              {/* Typing indicator */}
              {isLoading && (
                <div className="flex w-full justify-start px-4 py-5 md:px-8">
                  <div className="flex w-full max-w-4xl gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#142c26] text-[#d7f06c] shadow-sm">
                      <div className="flex gap-1">
                        <span className="h-1 w-1 animate-bounce rounded-full bg-current [animation-delay:-0.3s]"></span>
                        <span className="h-1 w-1 animate-bounce rounded-full bg-current [animation-delay:-0.15s]"></span>
                        <span className="h-1 w-1 animate-bounce rounded-full bg-current"></span>
                      </div>
                    </div>
                    <div className="pt-2 text-xs font-medium text-[#7b8982]">Finding the right assessments…</div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} className="h-4 shrink-0" />
            </div>
          )}
          </div>
        </main>

        <footer className="relative z-10 shrink-0 bg-linear-to-t from-[#f5f6f2] via-[#f5f6f2] to-transparent px-4 pb-5 pt-4 md:px-8 md:pb-7">
          <div className="mx-auto flex w-full max-w-4xl flex-col gap-2.5">
            <ChatInput onSend={sendMessage} isLoading={isLoading} />
            <p className="text-center text-[10px] tracking-wide text-[#89958e]">AI-assisted guidance · Always review assessment suitability for your context</p>
          </div>
        </footer>
      </div>
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
