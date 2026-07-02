import { ExternalLink, CheckSquare } from 'lucide-react';
import { Recommendation } from '../hooks/use-chat';

interface RecommendationCardProps {
  recommendation: Recommendation;
  index: number;
}

export function RecommendationCard({ recommendation, index }: RecommendationCardProps) {
  return (
    <div 
      className="bg-card border border-border/60 hover:border-border transition-colors rounded-xl p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4 w-full max-w-2xl mt-2 animate-in fade-in slide-in-from-bottom-2"
      style={{ animationDelay: `${index * 100}ms`, animationFillMode: 'both' }}
      data-testid="recommendation-card"
    >
      <div className="flex flex-col gap-1.5">
        <h4 className="font-semibold text-foreground tracking-tight line-clamp-1" title={recommendation.name}>
          {recommendation.name}
        </h4>
        <div className="flex items-center">
          <span className="inline-flex items-center gap-1 rounded-md bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground border border-secondary-border">
            <CheckSquare className="w-3 h-3" />
            {recommendation.test_type}
          </span>
        </div>
      </div>
      
      <a
        href={recommendation.url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring whitespace-nowrap"
      >
        View on SHL
        <ExternalLink className="w-3.5 h-3.5" />
      </a>
    </div>
  );
}
