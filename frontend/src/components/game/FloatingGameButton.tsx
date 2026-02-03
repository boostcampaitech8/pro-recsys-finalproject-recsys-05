interface FloatingGameButtonProps {
  onClick: () => void;
}

export function FloatingGameButton({ onClick }: FloatingGameButtonProps) {
  return (
    <button
      onClick={onClick}
      className="fixed left-0 z-30 h-16 group transition-all duration-500 hover:left-0"
      style={{
        top: 'calc(50vh - 120px)',
        display: 'flex',
        alignItems: 'center',
        gap: '0',
      }}
    >
      {/* Sliding tab background */}
      <div
        className="flex items-center gap-3 px-4 py-3 rounded-r-2xl transition-all duration-500 group-hover:shadow-2xl"
        style={{
          background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.25), rgba(5, 150, 105, 0.15))',
          border: '1px solid rgba(16, 185, 129, 0.6)',
          backdropFilter: 'blur(10px)',
          marginLeft: '0',
        }}
      >
        {/* Label */}
        <span className="text-sm font-bold text-emerald-300 whitespace-nowrap transition-all duration-300 group-hover:text-emerald-200">
          PLAY
        </span>

        {/* Game Controller Icon SVG */}
        <svg
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-emerald-400 group-hover:text-emerald-300 transition-colors duration-300"
        >
          {/* Controller body */}
          <path d="M6 12c0-3.3 2.7-6 6-6s6 2.7 6 6" />

          {/* Left buttons (D-pad style) */}
          <circle cx="8" cy="11" r="1.5" fill="currentColor" />
          <circle cx="6" cy="13" r="1.5" fill="currentColor" />
          <circle cx="10" cy="13" r="1.5" fill="currentColor" />

          {/* Right buttons (ABXY style) */}
          <circle cx="16" cy="11" r="1.5" fill="currentColor" />
          <circle cx="14" cy="13" r="1.5" fill="currentColor" />
          <circle cx="18" cy="13" r="1.5" fill="currentColor" />

          {/* Controller handles */}
          <path d="M4 14c-1 1-1 3 0 4" stroke="currentColor" strokeWidth="1.5" />
          <path d="M20 14c1 1 1 3 0 4" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      </div>

      {/* Glow effect */}
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-r-2xl blur-xl -z-10"
        style={{
          background: 'radial-gradient(ellipse at center, rgba(16, 185, 129, 0.3), transparent)',
        }}
      />

      <style>{`
        @keyframes float {
          0%, 100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(-8px);
          }
        }

        button {
          animation: float 3s ease-in-out infinite;
        }

        button:hover {
          animation: none;
        }
      `}</style>
    </button>
  );
}
