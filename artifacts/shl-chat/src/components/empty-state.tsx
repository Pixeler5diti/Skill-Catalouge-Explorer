import { BrainCircuit, Sparkles, Target, Zap } from 'lucide-react';

interface EmptyStateProps {
  onSelectPrompt: (prompt: string) => void;
}

export function EmptyState({ onSelectPrompt }: EmptyStateProps) {
  const suggestions = [
    {
      title: "Sales leadership roles",
      prompt: "Find assessments for a senior sales manager",
      icon: Target
    },
    {
      title: "Compare assessments",
      prompt: "Compare OPQ32r and SJT",
      icon: BrainCircuit
    },
    {
      title: "Time-constrained",
      prompt: "Need cognitive tests under 30 minutes",
      icon: Zap
    }
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full px-4 text-center animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-2xl mx-auto">
      <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mb-6 ring-1 ring-primary/20">
        <Sparkles className="w-8 h-8 text-primary" />
      </div>
      
      <h2 className="text-2xl font-bold tracking-tight text-foreground mb-2">
        SHL Assessment Recommender
      </h2>
      
      <p className="text-muted-foreground text-[15px] mb-10 max-w-md mx-auto">
        Your expert advisor for finding the perfect psychometric tests. Ask me to find, compare, or explain SHL assessments.
      </p>
      
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full">
        {suggestions.map((suggestion, i) => {
          const Icon = suggestion.icon;
          return (
            <button
              key={i}
              onClick={() => onSelectPrompt(suggestion.prompt)}
              className="flex flex-col items-center gap-3 p-4 rounded-xl border border-border/60 bg-card hover:bg-muted/50 hover:border-primary/30 transition-all text-left"
            >
              <div className="w-10 h-10 rounded-full bg-secondary/50 flex items-center justify-center text-primary">
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex flex-col items-center text-center">
                <span className="text-sm font-semibold text-foreground mb-1">
                  {suggestion.title}
                </span>
                <span className="text-xs text-muted-foreground line-clamp-2">
                  "{suggestion.prompt}"
                </span>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  );
}
