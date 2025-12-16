import React from "react";
import { Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { ActionTooltip } from "@/components/ui/action-tooltip";

interface LatencyIndicatorProps {
    latencyMs: number | null;
    className?: string;
}

export function LatencyIndicator({ latencyMs, className }: LatencyIndicatorProps) {
    // Determine quality tier based on actual latency
    const getTier = (ms: number | null): "good" | "fair" | "poor" => {
        if (ms === null) return "poor";
        if (ms <= 150) return "good";
        if (ms <= 300) return "fair";
        return "poor";
    };

    const tier = getTier(latencyMs);

    // Determine color based on tier
    const colorClass =
        tier === "good" ? "text-emerald-400" :
            tier === "fair" ? "text-yellow-400" :
                "text-red-400";

    // Label text with actual latency
    const labelText = latencyMs !== null
        ? `Latency: ${latencyMs}ms (${tier === "good" ? "Excellent" : tier === "fair" ? "Fair" : "Poor"})`
        : "Latency will be available after successful connection.";

    return (
        <div className={cn(
            "flex items-center justify-center w-8 h-8 rounded-full hover:bg-white/10 transition-colors relative group",
            className
        )}>
            <Activity className={cn("w-4 h-4", colorClass)} />
            <ActionTooltip
                label={labelText}
                side="top"
            />
        </div>
    );
}
