import { useEffect, ReactNode } from "react";

interface GameModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
}

export function GameModal({ isOpen, onClose, children }: GameModalProps) {
  useEffect(() => {
    const handleEscKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    if (isOpen) {
      window.addEventListener("keydown", handleEscKey);
      return () => window.removeEventListener("keydown", handleEscKey);
    }
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      {/* Modal container */}
      <div
        className="relative bg-slate-800 rounded-xl p-6 shadow-2xl border border-emerald-400/30 animate-fade-in-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-700 transition-colors z-10"
          aria-label="Close game"
        >
          <span className="text-lg text-slate-300 hover:text-slate-100">✕</span>
        </button>

        {/* Game content */}
        <div className="flex items-center justify-center">
          {children}
        </div>
      </div>
    </div>
  );
}
