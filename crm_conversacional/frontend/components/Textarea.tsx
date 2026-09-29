"use client";

import { cn } from "@/lib/utils";
import { useId, type TextareaHTMLAttributes } from "react";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  error?: string;
  hint?: string;
}

export function Textarea({ label, error, hint, className, id, ...props }: TextareaProps) {
  const generatedId = useId();
  const textareaId = id ?? generatedId;
  const describedById = error
    ? `${textareaId}-error`
    : hint
      ? `${textareaId}-hint`
      : undefined;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={textareaId} className="text-sm font-medium text-fg-soft">
        {label}
      </label>
      <textarea
        id={textareaId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedById}
        className={cn(
          "min-h-[8rem] resize-y rounded-lg border border-surface-border bg-surface px-3 py-2.5 text-sm text-fg",
          "placeholder:text-fg-faint",
          "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100",
          error && "border-red-500 focus:border-red-500 focus:ring-red-100",
          className,
        )}
        {...props}
      />
      {error && (
        <p id={`${textareaId}-error`} className="text-xs text-red-600 dark:text-red-300">
          {error}
        </p>
      )}
      {!error && hint && (
        <p id={`${textareaId}-hint`} className="text-xs text-fg-muted">
          {hint}
        </p>
      )}
    </div>
  );
}

export default Textarea;
