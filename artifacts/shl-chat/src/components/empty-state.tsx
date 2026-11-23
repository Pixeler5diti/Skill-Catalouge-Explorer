import { ArrowRight, ArrowUpRight, BrainCircuit, Clock3, Sparkles, Target } from 'lucide-react';

interface EmptyStateProps {
  onSelectPrompt: (prompt: string) => void;
}

export function EmptyState({ onSelectPrompt }: EmptyStateProps) {
  const suggestions = [
    {
      title: "Find by role",
      detail: "Build a shortlist around a position",
      prompt: "Find assessments for a senior sales manager",
      icon: Target
    },
    {
      title: "Compare options",
      detail: "Understand the differences",
      prompt: "Compare OPQ32r and SJT",
      icon: BrainCircuit
    },
    {
      title: "Fit a time limit",
      detail: "Find a focused, shorter assessment",
      prompt: "Need cognitive tests under 30 minutes",
      icon: Clock3
    }
  ];

  return (
    <div className="relative mx-auto flex w-full max-w-5xl flex-col items-start animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="absolute -right-4 -top-8 hidden h-64 w-64 rounded-full bg-[#d9e8ca]/50 blur-3xl md:block" />
      <div className="relative mb-7 inline-flex items-center gap-2 rounded-full border border-[#dfe5dc] bg-white/80 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.17em] text-[#65776c] shadow-sm">
        <Sparkles className="h-3.5 w-3.5 text-[#789846]" /> Your assessment workspace
      </div>

      <div className="relative grid w-full gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-end">
        <div className="pb-2">
          <h2 className="max-w-2xl text-[2.7rem] font-semibold leading-[1.04] tracking-[-0.06em] text-[#18352c] sm:text-6xl">
            Find the right fit.<br /><span className="font-normal italic text-[#789846]">Not just a test.</span>
          </h2>
          <p className="mt-5 max-w-lg text-sm leading-7 text-[#687870] sm:text-base">
            Explore SHL assessments with a little more context. Tell us about the role, the skills, or the decision you need to make.
          </p>
          <div className="mt-7 flex flex-wrap gap-x-5 gap-y-2 text-[11px] font-medium text-[#748279]">
            <span className="inline-flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-[#a7c65a]" /> Role-aware discovery</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-[#a7c65a]" /> Clear comparisons</span>
          </div>
        </div>

        <div className="relative hidden min-h-[220px] overflow-hidden rounded-[28px] bg-[#18352c] p-6 text-white shadow-xl shadow-[#18352c]/10 sm:block">
          <div className="absolute -right-10 -top-16 h-56 w-56 rounded-full border border-white/10" />
          <div className="absolute -right-1 -top-7 h-40 w-40 rounded-full border border-white/10" />
          <div className="absolute bottom-0 right-10 h-24 w-24 rounded-full bg-[#d7f06c]/10 blur-2xl" />
          <div className="relative flex h-full flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="rounded-full border border-white/15 bg-white/[0.07] px-3 py-1 text-[10px] font-semibold tracking-wide text-white/65">A smarter starting point</span>
              <ArrowUpRight className="h-4 w-4 text-[#d7f06c]" />
            </div>
            <div className="mt-10">
              <p className="text-2xl font-medium leading-snug tracking-tight">The best shortlist<br />starts with <span className="text-[#d7f06c]">your goals.</span></p>
              <p className="mt-3 max-w-xs text-xs leading-5 text-white/50">Ask naturally. Refine by duration, language, or job level as you go.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="relative mt-11 flex w-full items-end justify-between border-b border-[#dfe5dc] pb-3">
        <div><p className="text-sm font-bold tracking-tight text-[#233b32]">Start with a direction</p><p className="mt-1 text-xs text-[#87938c]">Choose a prompt or write your own below.</p></div>
        <span className="hidden text-[10px] font-semibold uppercase tracking-[0.15em] text-[#9aa59f] sm:block">Suggested paths</span>
      </div>

      <div className="relative mt-4 grid w-full grid-cols-1 gap-3 sm:grid-cols-3">
        {suggestions.map((suggestion, i) => {
          const Icon = suggestion.icon;
          return (
            <button
              key={i}
              onClick={() => onSelectPrompt(suggestion.prompt)}
              className="group flex min-h-[156px] flex-col rounded-2xl border border-[#e2e7df] bg-white/85 p-4 text-left shadow-[0_4px_18px_-14px_rgba(24,53,44,0.3)] transition duration-200 hover:-translate-y-1 hover:border-[#b8c99e] hover:bg-white hover:shadow-lg hover:shadow-[#18352c]/[0.07]"
            >
              <div className="flex w-full items-center justify-between">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#edf2e8] text-[#698446] transition group-hover:bg-[#dff0be]">
                  <Icon className="h-4 w-4" />
                </div>
                <ArrowRight className="h-4 w-4 text-[#aab4ad] transition group-hover:translate-x-1 group-hover:text-[#698446]" />
              </div>
              <div className="mt-auto pt-5">
                <span className="block text-sm font-bold tracking-tight text-[#263c33]">{suggestion.title}</span>
                <span className="mt-1 block text-xs leading-5 text-[#849088]">{suggestion.detail}</span>
              </div>
            </button>
          )
        })}
      </div>
      <button onClick={() => onSelectPrompt('Help me find the right SHL assessments')} className="relative mt-5 inline-flex items-center gap-2 text-xs font-semibold text-[#71856a] transition hover:text-[#304b38]">
        Not sure where to start? Ask for help <ArrowRight className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
