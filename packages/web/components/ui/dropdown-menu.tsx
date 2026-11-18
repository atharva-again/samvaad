"use client";

import { Menu } from "@base-ui/react/menu";
import { CheckIcon, ChevronRightIcon, CircleIcon } from "lucide-react";
import * as React from "react";
import { cn } from "@/lib/utils";

function DropdownMenu(props: React.ComponentProps<typeof Menu.Root>) {
  return <Menu.Root data-slot="dropdown-menu" {...props} />;
}

function DropdownMenuPortal(props: React.ComponentProps<typeof Menu.Portal>) {
  return <Menu.Portal data-slot="dropdown-menu-portal" {...props} />;
}

type TriggerProps = React.ComponentProps<typeof Menu.Trigger> & {
  asChild?: boolean;
};

function DropdownMenuTrigger({ asChild = false, children, ...props }: TriggerProps) {
  return (
    <Menu.Trigger
      data-slot="dropdown-menu-trigger"
      render={asChild && React.isValidElement(children) ? children : undefined}
      {...props}
    >
      {asChild ? undefined : children}
    </Menu.Trigger>
  );
}

type PositioningProps = Pick<
  React.ComponentProps<typeof Menu.Positioner>,
  "align" | "side" | "sideOffset" | "alignOffset"
>;

type ContentProps = Omit<React.ComponentProps<typeof Menu.Popup>, "className"> &
  PositioningProps & { className?: string };

function DropdownMenuContent({
  className,
  align = "center",
  side = "bottom",
  sideOffset = 4,
  alignOffset,
  children,
  ...props
}: ContentProps) {
  return (
    <Menu.Portal>
      <Menu.Positioner
        align={align}
        side={side}
        sideOffset={sideOffset}
        alignOffset={alignOffset}
        className="z-50"
      >
        <Menu.Popup
          data-slot="dropdown-menu-content"
          className={cn(
            "bg-popover text-popover-foreground data-[open]:animate-in data-[closed]:animate-out data-[closed]:fade-out-0 data-[open]:fade-in-0 data-[closed]:zoom-out-95 data-[open]:zoom-in-95 z-50 max-h-[var(--available-height)] min-w-[8rem] origin-[var(--transform-origin)] overflow-x-hidden overflow-y-auto rounded-md border p-1 shadow-md outline-none",
            className,
          )}
          {...props}
        >
          {children}
        </Menu.Popup>
      </Menu.Positioner>
    </Menu.Portal>
  );
}

function DropdownMenuGroup(props: React.ComponentProps<typeof Menu.Group>) {
  return <Menu.Group data-slot="dropdown-menu-group" {...props} />;
}

type ItemProps = Omit<React.ComponentProps<typeof Menu.Item>, "className"> & {
  className?: string;
  inset?: boolean;
  variant?: "default" | "destructive";
};

function DropdownMenuItem({ className, inset, variant = "default", ...props }: ItemProps) {
  return (
    <Menu.Item
      data-slot="dropdown-menu-item"
      data-inset={inset}
      data-variant={variant}
      className={cn(
        "data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground data-[variant=destructive]:text-destructive data-[variant=destructive]:data-[highlighted]:bg-destructive/10 data-[variant=destructive]:data-[highlighted]:text-destructive relative flex cursor-default items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none select-none data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[inset]:pl-8 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className,
      )}
      {...props}
    />
  );
}

type CheckboxItemProps = Omit<React.ComponentProps<typeof Menu.CheckboxItem>, "className"> & {
  className?: string;
};

function DropdownMenuCheckboxItem({ className, children, ...props }: CheckboxItemProps) {
  return (
    <Menu.CheckboxItem
      data-slot="dropdown-menu-checkbox-item"
      className={cn(
        "data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground relative flex cursor-default items-center gap-2 rounded-sm py-1.5 pr-2 pl-8 text-sm outline-none select-none data-[disabled]:pointer-events-none data-[disabled]:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className,
      )}
      {...props}
    >
      <span className="pointer-events-none absolute left-2 flex size-3.5 items-center justify-center">
        <Menu.CheckboxItemIndicator>
          <CheckIcon className="size-4" />
        </Menu.CheckboxItemIndicator>
      </span>
      {children}
    </Menu.CheckboxItem>
  );
}

function DropdownMenuRadioGroup(props: React.ComponentProps<typeof Menu.RadioGroup>) {
  return <Menu.RadioGroup data-slot="dropdown-menu-radio-group" {...props} />;
}

function DropdownMenuRadioItem({
  className,
  children,
  ...props
}: React.ComponentProps<typeof Menu.RadioItem>) {
  return (
    <Menu.RadioItem
      data-slot="dropdown-menu-radio-item"
      className={cn(
        "data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground relative flex cursor-default items-center gap-2 rounded-sm py-1.5 pr-2 pl-8 text-sm outline-none select-none data-[disabled]:pointer-events-none data-[disabled]:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className,
      )}
      {...props}
    >
      <span className="pointer-events-none absolute left-2 flex size-3.5 items-center justify-center">
        <Menu.RadioItemIndicator>
          <CircleIcon className="size-2 fill-current" />
        </Menu.RadioItemIndicator>
      </span>
      {children}
    </Menu.RadioItem>
  );
}

type LabelProps = Omit<React.ComponentProps<typeof Menu.GroupLabel>, "className"> & {
  className?: string;
  inset?: boolean;
};

function DropdownMenuLabel({ className, inset, ...props }: LabelProps) {
  return (
    <Menu.GroupLabel
      data-slot="dropdown-menu-label"
      data-inset={inset}
      className={cn("px-2 py-1.5 text-sm font-medium data-[inset]:pl-8", className)}
      {...props}
    />
  );
}

function DropdownMenuSeparator({
  className,
  ...props
}: Omit<React.ComponentProps<typeof Menu.Separator>, "className"> & {
  className?: string;
}) {
  return (
    <Menu.Separator
      data-slot="dropdown-menu-separator"
      className={cn("bg-border -mx-1 my-1 h-px", className)}
      {...props}
    />
  );
}

function DropdownMenuShortcut({ className, ...props }: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="dropdown-menu-shortcut"
      className={cn("text-muted-foreground ml-auto text-xs tracking-widest", className)}
      {...props}
    />
  );
}

function DropdownMenuSub(props: React.ComponentProps<typeof Menu.SubmenuRoot>) {
  return <Menu.SubmenuRoot data-slot="dropdown-menu-sub" {...props} />;
}

type SubTriggerProps = Omit<React.ComponentProps<typeof Menu.SubmenuTrigger>, "className"> & {
  className?: string;
  inset?: boolean;
};

function DropdownMenuSubTrigger({ className, inset, children, ...props }: SubTriggerProps) {
  return (
    <Menu.SubmenuTrigger
      data-slot="dropdown-menu-sub-trigger"
      data-inset={inset}
      className={cn(
        "data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground data-[open]:bg-accent data-[open]:text-accent-foreground flex cursor-default items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none select-none data-[inset]:pl-8 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className,
      )}
      {...props}
    >
      {children}
      <ChevronRightIcon className="ml-auto size-4" />
    </Menu.SubmenuTrigger>
  );
}

type SubContentProps = Omit<React.ComponentProps<typeof Menu.Popup>, "className"> & {
  className?: string;
};

function DropdownMenuSubContent({ className, children, ...props }: SubContentProps) {
  return (
    <Menu.Portal>
      <Menu.Positioner side="inline-end" align="start" sideOffset={4}>
        <Menu.Popup
          data-slot="dropdown-menu-sub-content"
          className={cn(
            "bg-popover text-popover-foreground data-[open]:animate-in data-[closed]:animate-out data-[closed]:fade-out-0 data-[open]:fade-in-0 data-[closed]:zoom-out-95 data-[open]:zoom-in-95 z-50 min-w-[8rem] origin-[var(--transform-origin)] overflow-hidden rounded-md border p-1 shadow-lg outline-none",
            className,
          )}
          {...props}
        >
          {children}
        </Menu.Popup>
      </Menu.Positioner>
    </Menu.Portal>
  );
}

export {
  DropdownMenu,
  DropdownMenuPortal,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuItem,
  DropdownMenuCheckboxItem,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
};
