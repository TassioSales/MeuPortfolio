import { type ReactNode } from "react";

interface Props {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      {icon && (
        <div className="mb-4 p-4 rounded-2xl bg-surface-raised border border-border text-text-muted">
          {icon}
        </div>
      )}
      <p className="text-base font-semibold text-text-primary mb-1">{title}</p>
      {description && (
        <p className="text-sm text-text-muted max-w-xs mb-4">{description}</p>
      )}
      {action}
    </div>
  );
}
