import { RefreshCw, CheckCircle2, XCircle } from 'lucide-react';

interface HealthStatusProps {
  status: 'ok' | 'error' | 'loading';
}

export function HealthStatus({ status }: HealthStatusProps) {
  return (
    <div 
      className="flex items-center gap-1.5 text-xs font-medium" 
      data-testid="health-status"
    >
      {status === 'loading' && (
        <>
          <RefreshCw className="w-3.5 h-3.5 text-muted-foreground animate-spin" />
          <span className="text-muted-foreground">Connecting...</span>
        </>
      )}
      {status === 'ok' && (
        <>
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          <span className="text-emerald-600 dark:text-emerald-400">Connected</span>
        </>
      )}
      {status === 'error' && (
        <>
          <XCircle className="w-3.5 h-3.5 text-destructive" />
          <span className="text-destructive">Offline</span>
        </>
      )}
    </div>
  );
}
