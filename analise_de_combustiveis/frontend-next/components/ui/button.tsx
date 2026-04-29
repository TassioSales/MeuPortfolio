import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-full px-4 py-2 text-sm font-semibold transition",
  {
    variants: {
      variant: {
        default: "bg-accent text-ink hover:bg-accent/90",
        ghost: "bg-white/5 text-white hover:bg-white/10",
        outline: "border border-line text-white hover:bg-white/5",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export function Button({
  className,
  variant,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>) {
  return <button className={cn(buttonVariants({ variant }), className)} {...props} />;
}

