"use client";

import { Popover as BasePopover } from "@base-ui/react/popover";
import * as React from "react";
import { cn } from "@/lib/utils";

function Popover(props: React.ComponentProps<typeof BasePopover.Root>) {
  return <BasePopover.Root data-slot="popover" {...props} />;
}

type TriggerProps = React.ComponentProps<typeof BasePopover.Trigger> & {
  asChild?: boolean;
};

function PopoverTrigger({ asChild = false, children, ...props }: TriggerProps) {
  return (
    <BasePopover.Trigger
      data-slot="popover-trigger"
      render={asChild && React.isValidElement(children) ? children : undefined}
      {...props}
    >
      {asChild ? undefined : children}
    </BasePopover.Trigger>
  );
}

type ContentProps = Omit<React.ComponentProps<typeof BasePopover.Popup>, "className"> &
  Pick<
    React.ComponentProps<typeof BasePopover.Positioner>,
    "align" | "side" | "sideOffset" | "alignOffset"
  > & { className?: string };

function PopoverContent({
  className,
  align = "center",
  side = "bottom",
  sideOffset = 4,
  alignOffset,
  children,
  ...props
}: ContentProps) {
  return (
    <BasePopover.Portal>
      <BasePopover.Positioner
        align={align}
        side={side}
        sideOffset={sideOffset}
        alignOffset={alignOffset}
        className="z-50"
      >
        <BasePopover.Popup
          data-slot="popover-content"
          className={cn(
            "bg-popover text-popover-foreground data-[open]:animate-in data-[closed]:animate-out data-[closed]:fade-out-0 data-[open]:fade-in-0 data-[closed]:zoom-out-95 data-[open]:zoom-in-95 z-50 w-72 origin-[var(--transform-origin)] rounded-md border p-4 shadow-md outline-none",
            className,
          )}
          {...props}
        >
          {children}
        </BasePopover.Popup>
      </BasePopover.Positioner>
    </BasePopover.Portal>
  );
}

export { Popover, PopoverTrigger, PopoverContent };
