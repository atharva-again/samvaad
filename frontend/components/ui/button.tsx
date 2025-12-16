import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cn } from "@/lib/utils"

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link" | "signal"
  size?: "default" | "sm" | "lg" | "icon"
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"

    const baseStyles = "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 cursor-pointer"

    const variants = {
      default: "bg-surface text-text-primary border border-white/10 hover:bg-white/5 hover:border-white/20 shadow-sm",
      destructive: "bg-red-900/20 text-red-400 border border-red-900/50 hover:bg-red-900/30",
      outline: "border border-white/10 bg-transparent hover:bg-white/5 text-text-primary",
      secondary: "bg-white/5 text-text-primary hover:bg-white/10",
      ghost: "hover:bg-white/5 text-text-secondary hover:text-text-primary",
      link: "text-accent underline-offset-4 hover:underline",
      signal: "bg-signal/10 text-signal border border-signal/20 hover:bg-signal/20 shadow-[0_0_15px_rgba(16,185,129,0.1)]"
    }

    const sizes = {
      default: "h-9 px-4 py-2",
      sm: "h-8 rounded-md px-3 text-xs",
      lg: "h-10 rounded-md px-8",
      icon: "h-9 w-9",
    }

    return (
      <Comp
        className={cn(
            baseStyles,
            variants[variant] || variants.default,
            sizes[size],
            className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }
