import React from 'react';
import { useApp } from '../../context/AppContext';
import { CheckCircle2, AlertTriangle, AlertCircle, Info } from 'lucide-react';

export function ToastContainer() {
  const { toasts } = useApp();

  if (!toasts.length) return null;

  const icons = {
    success: <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />,
    error: <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />,
    warning: <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />,
    info: <Info className="w-4 h-4 text-cyan-400 shrink-0" />,
  };

  const styles = {
    success: 'bg-emerald-950/95 border-emerald-800 text-emerald-200',
    error: 'bg-rose-950/95 border-rose-800 text-rose-200',
    warning: 'bg-amber-950/95 border-amber-800 text-amber-200',
    info: 'bg-slate-900/95 border-indigo-800 text-slate-100',
  };

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`pointer-events-auto flex items-start gap-2.5 p-3 rounded-xl border shadow-xl text-xs backdrop-blur-md transition-all duration-300 animate-in fade-in slide-in-from-bottom-2 ${
            styles[toast.type] || styles.info
          }`}
        >
          {icons[toast.type] || icons.info}
          <div className="flex-1 font-medium leading-relaxed">{toast.message}</div>
        </div>
      ))}
    </div>
  );
}
