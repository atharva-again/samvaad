import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Paperclip, Folder, Upload } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { usePlatform } from "@/hooks/usePlatform"; // Assuming we want to show shortcut in title?
import { ActionTooltip } from "@/components/ui/action-tooltip";

interface AttachmentButtonProps {
    onUploadClick: () => void;
    onViewFilesClick: () => void;
}

export const AttachmentButton: React.FC<AttachmentButtonProps> = ({
    onUploadClick,
    onViewFilesClick
}) => {
    const [isHovered, setIsHovered] = useState(false);
    const timeoutRef = React.useRef<NodeJS.Timeout | null>(null);
    const { modifier } = usePlatform();

    const handleMouseEnter = () => {
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
        }
        setIsHovered(true);
    };

    const handleMouseLeave = () => {
        timeoutRef.current = setTimeout(() => {
            setIsHovered(false);
        }, 100); // 100ms delay
    };

    return (
        <div
            className="relative flex items-center justify-center"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
        >
            <Button
                type="button"
                size="icon"
                className="h-16 w-16 rounded-full bg-black/40 backdrop-blur-2xl border border-white/10 hover:bg-white/10 text-white shadow-2xl shrink-0 transition-all z-20 relative"
                onClick={onUploadClick}
                title={`Attach File (${modifier}+A)`}
            >
                <Paperclip className="w-6 h-6" />
            </Button>

            <AnimatePresence>
                {isHovered && (
                    <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 5, scale: 0.95 }}
                        transition={{ duration: 0.2 }}
                        className="absolute bottom-full mb-3 left-0 bg-black/90 backdrop-blur-xl border border-white/10 rounded-2xl p-2 shadow-2xl min-w-[200px] flex flex-col gap-1 z-30"
                    >
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                onViewFilesClick();
                            }}
                            className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-white/10 transition-colors w-full text-left group cursor-pointer relative"
                        >
                            <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400 group-hover:bg-indigo-500/30 transition-colors">
                                <Folder className="w-4 h-4" />
                            </div>
                            <span className="text-sm font-medium text-white/90">
                                View Sources
                            </span>
                            <ActionTooltip label="View Sources" shortcut={`${modifier}+S`} side="right" />
                        </button>

                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                onUploadClick();
                            }}
                            className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-white/10 transition-colors w-full text-left group cursor-pointer relative"
                        >
                            <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400 group-hover:bg-emerald-500/30 transition-colors">
                                <Upload className="w-4 h-4" />
                            </div>
                            <span className="text-sm font-medium text-white/90">
                                Add Sources
                            </span>
                            <ActionTooltip label="Add Sources" shortcut={`${modifier}+A`} side="right" />
                        </button>

                        {/* Arrow */}
                        <div className="absolute top-full left-6 -mt-1.5 w-3 h-3 bg-black/90 border-r border-b border-white/10 rotate-45 transform" />
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};
