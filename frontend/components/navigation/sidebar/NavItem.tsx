import React from "react";
import { cn } from "@/lib/utils";
import { ActionTooltip } from "@/components/ui/action-tooltip";

interface NavItemProps {
    icon: React.ReactNode;
    label: string;
    isExpanded: boolean;
    isActive?: boolean;
    onClick?: () => void;
    shortcut?: string;
    tooltipLabel?: string;
    tooltipShortcut?: string;
}

export function NavItem({
    icon,
    label,
    isExpanded,
    isActive,
    onClick,
    shortcut,
    tooltipLabel,
    tooltipShortcut
}: NavItemProps) {
    return (
        <button
            onClick={onClick}
            className={cn(
                "w-full flex items-center transition-all duration-150 relative group rounded-lg cursor-pointer",
                isExpanded ? "gap-3 px-3 py-2" : "justify-center py-2",
                isActive
                    ? "bg-white/10 text-white"
                    : "text-white/50 hover:text-white hover:bg-white/5"
            )}
        >
            <div className="w-5 h-5 flex items-center justify-center shrink-0">
                {icon}
            </div>
            {isExpanded && (
                <span className="text-[13px] font-medium flex-1 text-left truncate">
                    {label}
                </span>
            )}
            {isExpanded && shortcut && (
                <span className="text-[11px] text-white/30 font-mono">
                    {shortcut}
                </span>
            )}

            {!isExpanded && (
                <ActionTooltip
                    label={tooltipLabel || label}
                    shortcut={tooltipShortcut}
                    side="right"
                />
            )}
        </button>
    );
}
