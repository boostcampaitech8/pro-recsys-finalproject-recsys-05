import budocki from "@/assets/budocki.png";

interface HeaderProps {
  onClear?: () => void;
}

export function Header({ onClear }: HeaderProps) {
  return (
    <div className="w-full flex flex-col items-center relative">
      {/* Clear 버튼 */}
      {onClear && (
        <button
          onClick={onClear}
          className="absolute top-0 right-12 text-emerald-400 hover:text-emerald-300 transition-colors text-sm font-semibold"
          title="채팅 초기화"
        >
          🗑️ Clear
        </button>
      )}

      <img
        src={budocki}
        alt="Logo"
        className="w-14 h-auto m-auto"
        loading="lazy"
      />
      <p className="text-white mb-2">Budocki</p>
      <h1 className="text-5xl font-bold text-white mb-2">
        Welcome to TailorPlay!
      </h1>

      <p className="text-l text-gray-300 mb-4">
        A personalized Steam game recommendation chatbot.
      </p>
    </div>
  );
}
