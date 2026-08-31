/** Shared presentational building blocks, all in the VANGUARD design language. */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Upload, X, Loader2, Check, AlertTriangle } from 'lucide-react';

/* ------------------------------------------------------------------ */
/* Ambient animated gradient — replaces the hero video.                */
/* Three drifting radial blobs in the brand palette over the ink base. */
/* ------------------------------------------------------------------ */
export function GradientField({ intense = false }: { intense?: boolean }) {
  return (
    <div aria-hidden className="ambient pointer-events-none absolute inset-0 overflow-hidden bg-ink">
      <div
        className="animate-drift absolute -left-[20%] -top-[30%] h-[85vh] w-[85vh] rounded-full blur-[110px]"
        style={{
          background: `radial-gradient(circle, rgba(0,210,255,${intense ? 0.42 : 0.2}) 0%, rgba(0,210,255,0) 68%)`,
        }}
      />
      <div
        className="animate-drift-slow absolute -right-[15%] top-[5%] h-[75vh] w-[75vh] rounded-full blur-[120px]"
        style={{
          background: `radial-gradient(circle, rgba(11,37,81,${intense ? 0.95 : 0.65}) 0%, rgba(11,37,81,0) 70%)`,
        }}
      />
      <div
        className="animate-drift absolute bottom-[-35%] left-[25%] h-[70vh] w-[70vh] rounded-full blur-[130px]"
        style={{
          animationDelay: '-9s',
          background: `radial-gradient(circle, rgba(164,244,253,${intense ? 0.22 : 0.11}) 0%, rgba(164,244,253,0) 68%)`,
        }}
      />
      <div
        className="animate-drift-slow absolute right-[10%] bottom-[-20%] h-[60vh] w-[60vh] rounded-full blur-[120px]"
        style={{
          animationDelay: '-16s',
          background: `radial-gradient(circle, rgba(61,129,227,${intense ? 0.3 : 0.15}) 0%, rgba(61,129,227,0) 70%)`,
        }}
      />
      {/* Vignette so overlaid text always keeps contrast. */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse at 50% 0%, rgba(12,12,12,.15), rgba(12,12,12,.82) 72%), linear-gradient(to bottom, rgba(12,12,12,.35), #0c0c0c 96%)',
        }}
      />
      {/* Fine grain keeps the large flat gradients from banding. */}
      <div
        className="absolute inset-0 opacity-[0.035] mix-blend-overlay"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='120' height='120' filter='url(%23n)'/%3E%3C/svg%3E\")",
        }}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Buttons                                                             */
/* ------------------------------------------------------------------ */
type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'ghost' | 'outline' | 'danger';
  busy?: boolean;
};

export function Button({ variant = 'primary', busy, className = '', children, ...rest }: BtnProps) {
  const base =
    'inline-flex items-center justify-center gap-2 text-[11px] sm:text-xs font-semibold uppercase tracking-widest transition disabled:opacity-40 disabled:cursor-not-allowed';
  const styles: Record<string, string> = {
    primary: 'bg-white text-black px-5 py-3 sm:px-7 sm:py-4 hover:bg-frost rounded-full',
    outline:
      'border border-white/30 px-6 py-3 hover:border-white/60 hover:bg-white/10 rounded-full text-white',
    ghost: 'px-4 py-2 text-white/60 hover:text-white rounded-full',
    danger:
      'border border-red-400/40 text-red-300 px-5 py-3 hover:bg-red-500/10 rounded-full',
  };
  return (
    <button className={`${base} ${styles[variant]} ${className}`} disabled={busy || rest.disabled} {...rest}>
      {busy && <Loader2 size={14} className="animate-spin" />}
      {children}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/* Form primitives                                                     */
/* ------------------------------------------------------------------ */
export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="grid gap-2">
      <span className="text-[10px] uppercase tracking-[0.18em] text-white/45">{label}</span>
      {children}
      {hint && <span className="text-[11px] leading-snug text-white/35">{hint}</span>}
    </label>
  );
}

const inputCls =
  'w-full rounded-xl border border-white/12 bg-black/35 px-3 py-2.5 text-sm text-white outline-none transition placeholder:text-white/25 focus:border-cyan/60';

export const Input = (p: React.InputHTMLAttributes<HTMLInputElement>) => (
  <input {...p} className={`${inputCls} ${p.className || ''}`} />
);

export const Select = (p: React.SelectHTMLAttributes<HTMLSelectElement>) => (
  <select {...p} className={`${inputCls} ${p.className || ''}`} />
);

export const Textarea = (p: React.TextareaHTMLAttributes<HTMLTextAreaElement>) => (
  <textarea {...p} className={`${inputCls} min-h-24 resize-y ${p.className || ''}`} />
);

/** Range slider with a live numeric readout. */
export function Range({
  label,
  value,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  suffix = '',
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
  suffix?: string;
}) {
  return (
    <label className="grid gap-1.5">
      <span className="flex items-baseline justify-between text-[10px] uppercase tracking-[0.18em] text-white/45">
        {label}
        <b className="font-inter text-xs normal-case tracking-normal text-white/80">
          {value}
          {suffix}
        </b>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full"
      />
    </label>
  );
}

export function Toggle({
  label,
  checked,
  onChange,
  disabled,
  hint,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  hint?: string;
}) {
  return (
    <div className="grid gap-1">
      <label
        className={`flex items-center gap-3 ${disabled ? 'opacity-50' : 'cursor-pointer'}`}
        onClick={() => !disabled && onChange(!checked)}
      >
        <span
          className={`relative h-5 w-9 shrink-0 rounded-full transition ${checked ? 'bg-cyan' : 'bg-white/15'}`}
        >
          <span
            className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${checked ? 'left-[1.15rem]' : 'left-0.5'}`}
          />
        </span>
        <span className="text-sm text-white/75">{label}</span>
      </label>
      {hint && <span className="pl-12 text-[11px] leading-snug text-white/35">{hint}</span>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* File uploader with drag & drop                                      */
/* ------------------------------------------------------------------ */
export function Uploader({
  title,
  hint,
  accept = 'image/*,video/*',
  file,
  onFile,
  multiple = false,
  onFiles,
}: {
  title: string;
  hint?: string;
  accept?: string;
  file?: File | null;
  onFile?: (f: File | null) => void;
  multiple?: boolean;
  onFiles?: (f: File[]) => void;
}) {
  const [over, setOver] = useState(false);
  const ref = useRef<HTMLInputElement>(null);

  const take = useCallback(
    (list: FileList | null) => {
      if (!list || !list.length) return;
      if (multiple) onFiles?.(Array.from(list));
      else onFile?.(list[0]);
    },
    [multiple, onFile, onFiles],
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        take(e.dataTransfer.files);
      }}
      onClick={() => ref.current?.click()}
      className={`grid min-h-32 cursor-pointer place-items-center rounded-2xl border border-dashed p-5 text-center transition ${
        over ? 'border-cyan bg-cyan/10' : 'border-white/20 bg-black/25 hover:border-cyan/50'
      }`}
    >
      <input
        ref={ref}
        type="file"
        accept={accept}
        multiple={multiple}
        className="hidden"
        onChange={(e) => take(e.target.files)}
      />
      <div>
        <Upload className="mx-auto mb-3 text-white/45" size={22} />
        <div className="text-sm text-white/70">{file ? file.name : title}</div>
        {hint && !file && <div className="mt-1 text-[11px] text-white/35">{hint}</div>}
        {file && (
          <button
            className="mt-2 text-[11px] text-white/40 underline hover:text-white/70"
            onClick={(e) => {
              e.stopPropagation();
              onFile?.(null);
            }}
          >
            <X size={11} className="inline" /> убрать
          </button>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Layout & feedback                                                   */
/* ------------------------------------------------------------------ */
export function Panel({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <section className={`glass rounded-3xl p-5 sm:p-6 ${className}`}>{children}</section>;
}

export function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-4 font-podium text-lg uppercase tracking-wide text-white sm:text-xl">
      {children}
    </h2>
  );
}

/** Inline status line: idle / busy / ok / error. */
export function Status({ text, kind }: { text: string; kind?: 'ok' | 'err' | 'busy' }) {
  if (!text) return null;
  const color =
    kind === 'err' ? 'text-red-300' : kind === 'ok' ? 'text-cyan' : 'text-white/55';
  const Icon = kind === 'err' ? AlertTriangle : kind === 'ok' ? Check : Loader2;
  return (
    <div className={`mt-3 flex items-start gap-2 text-xs ${color}`}>
      <Icon size={13} className={`mt-0.5 shrink-0 ${kind === 'busy' ? 'animate-spin' : ''}`} />
      <span className="leading-snug">{text}</span>
    </div>
  );
}

export function Empty({ text }: { text: string }) {
  return (
    <div className="grid min-h-64 place-items-center rounded-2xl border border-white/10 bg-black/20 text-center text-sm text-white/35">
      {text}
    </div>
  );
}

export function Spinner({ text }: { text: string }) {
  return (
    <div className="grid min-h-64 place-items-center gap-3 text-white/45">
      <Loader2 className="mx-auto animate-spin" />
      <span className="text-sm">{text}</span>
    </div>
  );
}

/** Progress bar 0..100. */
export function Progress({ value }: { value: number }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
      <div
        className="h-full rounded-full bg-gradient-to-r from-deep via-cyan to-frost transition-all duration-300"
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    addEventListener('keydown', h);
    return () => removeEventListener('keydown', h);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-[60] grid place-items-center bg-black/80 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="glass max-h-[88vh] w-full max-w-lg overflow-auto rounded-3xl p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-5 flex items-center justify-between">
          <h3 className="font-podium text-xl uppercase tracking-wide">{title}</h3>
          <button onClick={onClose} className="text-white/50 hover:text-white">
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

/** Object URL that is revoked when the source blob changes or unmounts. */
export function useObjectUrl(blob: Blob | null) {
  const [url, setUrl] = useState<string>('');
  useEffect(() => {
    if (!blob) {
      setUrl('');
      return;
    }
    const u = URL.createObjectURL(blob);
    setUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [blob]);
  return url;
}
