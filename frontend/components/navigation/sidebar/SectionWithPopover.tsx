import React, { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface SectionWithPopoverProps {
    icon: React.ReactNode;
    label: string;
    isExpanded: boolean;
    children?: React.ReactNode;
    popoverContent: React.ReactNode;
    forceOpen?: boolean;
}

export function SectionWithPopover({
    icon,
    label,
    isExpanded,
    children,
    popoverContent,
    forceOpen = false
}: SectionWithPopoverProps) {
    const [showPopover, setShowPopover] = useState(false);
    const timeoutRef = useRef<NodeJS.Timeout | null>(null);
    const prevForceOpenRef = useRef(forceOpen);
    const shouldShow = (showPopover || forceOpen) && !isExpanded;

    // When dropdown closes (forceOpen: true -> false), close the popover too
    // This handles the case where user deletes an item from the dropdown
    React.useEffect(() => {
        if (prevForceOpenRef.current && !forceOpen) {
            // Dropdown just closed, close the popover after a short delay
            timeoutRef.current = setTimeout(() => {
                setShowPopover(false);
            }, 150);
        }
        prevForceOpenRef.current = forceOpen;
    }, [forceOpen]);

    const handleMouseEnter = () => {
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
        }
        if (!isExpanded) setShowPopover(true);
    };

    const handleMouseLeave = () => {
        timeoutRef.current = setTimeout(() => {
            setShowPopover(false);
        }, 100);
    };

    return (
        <div
            className="relative"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
        >
            {/* Section Header */}
            <div className={cn(
                "flex items-center rounded-lg transition-all duration-150 w-full",
                isExpanded ? "gap-3 px-3 py-2" : "justify-center py-2",
                "text-white/50 hover:text-white hover:bg-white/5 cursor-pointer"
            )}>
                <div className="w-5 h-5 flex items-center justify-center shrink-0">
                    {icon}
                </div>
                {isExpanded && (
                    <span className="text-[11px] font-medium text-inherit uppercase tracking-wider">
                        {label}
                    </span>
                )}
            </div>

            {/* Inline Content when Expanded */}
            {isExpanded && children && (
                <div className="space-y-0.5">
                    {children}
                </div>
            )}

            {/* Hover Popover when Collapsed */}
            <AnimatePresence>
                {shouldShow && (
                    <motion.div
                        initial={{ opacity: 0, x: -8, scale: 0.95 }}
                        animate={{ opacity: 1, x: 0, scale: 1 }}
                        exit={{ opacity: 0, x: -8, scale: 0.95 }}
                        transition={{ duration: 0.12, ease: "easeOut" }}
                        className="absolute left-full top-0 ml-2 z-[100]"
                        onMouseEnter={handleMouseEnter}
                        onMouseLeave={handleMouseLeave}
                    >
                        <div className="bg-[#0F0F0F] border border-white/10 rounded-xl shadow-2xl min-w-[240px] max-w-[300px] overflow-hidden">
                            {popoverContent}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
