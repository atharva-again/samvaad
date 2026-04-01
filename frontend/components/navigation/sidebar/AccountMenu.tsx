import { ChevronRight, HelpCircle, LogOut, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

interface AccountMenuProps {
	onClose: () => void;
	onLogout: () => void;
	onSettingsOpen: () => void;
}

export function AccountMenu({ onClose, onLogout, onSettingsOpen }: AccountMenuProps) {
	const menuItems = [
		{
			icon: <Settings className="w-4 h-4" />,
			label: "Settings",
			onClick: onSettingsOpen,
		},
		{
			icon: <HelpCircle className="w-4 h-4" />,
			label: "Help",
			hasSubmenu: true,
			onClick: () => {},
		},
		{
			icon: <LogOut className="w-4 h-4" />,
			label: "Sign Out",
			onClick: onLogout,
			isDanger: true,
		},
	];

	return (
		<div className="py-2 min-w-[160px]">
			{menuItems.map((item, i) => (
				<button
					key={item.label}
					type="button"
					onClick={() => {
						onClose();
						item.onClick();
					}}
					className={cn(
						"w-[calc(100%-8px)] flex items-center gap-3 px-2 py-2 mx-1 rounded-md text-[13px] transition-colors cursor-pointer",
						item.isDanger
							? "text-red-400 hover:text-red-300 hover:bg-white/5"
							: "text-white/70 hover:text-white hover:bg-white/5",
					)}
				>
					{/* Icon inherits color from parent button */}
					{item.icon}
					<span className="flex-1 text-left">{item.label}</span>
					{item.hasSubmenu && (
						<ChevronRight className="w-3 h-3 text-white/30" />
					)}
				</button>
			))}
		</div>
	);
}
