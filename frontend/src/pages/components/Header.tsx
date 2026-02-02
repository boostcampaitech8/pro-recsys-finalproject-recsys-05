export function Header() {
  return (
    <div className="flex items-center gap-3">
      {/* 로고 - 네온 글로우 다이아몬드 스타일 */}
      <div className="flex items-center justify-center w-10 h-10 relative">
        <div
          className="absolute w-6 h-6 border-2 border-emerald-400 shadow-lg shadow-emerald-500/60"
          style={{ transform: 'rotate(45deg)' }}
        ></div>
        <div className="absolute w-2 h-2 bg-emerald-400 rounded-full shadow-lg shadow-emerald-400/80"></div>
      </div>

      {/* 텍스트 */}
      <div>
        <h1 className="text-lg font-bold text-white">TailorPlay</h1>
        <p className="text-xs text-slate-400">Game AI Assistant</p>
      </div>
    </div>
  );
}
