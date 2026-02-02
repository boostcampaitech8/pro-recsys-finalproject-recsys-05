export function Header() {
  return (
    <div className="flex items-center gap-3">
      {/* 로고 */}
      <div className="flex items-center justify-center w-10 h-10 bg-linear-to-br from-emerald-500 to-emerald-700 rounded-lg">
        <span className="text-lg font-bold text-white">TP</span>
      </div>

      {/* 텍스트 */}
      <div>
        <h1 className="text-lg font-bold text-white">TailorPlay</h1>
        <p className="text-xs text-slate-400">Game AI Assistant</p>
      </div>
    </div>
  );
}
