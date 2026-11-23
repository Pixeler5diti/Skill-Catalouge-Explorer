import { ExternalLink, CheckSquare } from 'lucide-react';
import { Recommendation } from '../hooks/use-chat';

interface RecommendationCardProps {
  recommendation: Recommendation;
  index: number;
}

export function RecommendationCard({ recommendation, index }: RecommendationCardProps) {
  return (
    <div 
      className="group bg-white border border-[#e2e7df] hover:border-[#b8c99e] transition-all rounded-2xl p-4 shadow-[0_5px_20px_-15px_rgba(24,53,44,0.35)] flex flex-col sm:flex-row sm:items-center justify-between gap-4 w-full max-w-2xl mt-2 animate-in fade-in slide-in-from-bottom-2"
      style={{ animationDelay: `${index * 100}ms`, animationFillMode: 'both' }}
      data-testid="recommendation-card"
    >
      <div className="flex min-w-0 flex-col gap-2">
        <h4 className="font-bold text-[#263c33] tracking-tight line-clamp-2" title={recommendation.name}>
          {recommendation.name}
        </h4>
        <div className="flex items-center">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#f0f4eb] px-2.5 py-1 text-[10px] font-semibold text-[#637b4c] border border-[#e5ebdd]">
            <CheckSquare className="w-3 h-3" />
            {recommendation.test_type}
          </span>
        </div>
      </div>
      
      <a
        href={recommendation.url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#18352c] px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition-all hover:bg-[#294b3f] hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#9dbb72] whitespace-nowrap"
      >
        View on SHL
        <ExternalLink className="w-3.5 h-3.5" />
      </a>
    </div>
  );
}
