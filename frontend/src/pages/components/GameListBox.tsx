export function GameListBox() {
  return (
    <div className="w-full mt-10 flex gap-5 text-emerald-300 p-6 bg-slate-800 rounded-lg shadow-lg border border-emerald-500/30">
      <div className="w-32 h-32 bg-emerald-900/30 rounded-lg flex items-center justify-center text-emerald-400 border border-emerald-500/50 hover:bg-emerald-900/50 transition-colors">
        1번 게임
      </div>
      <div className="w-32 h-32 bg-emerald-900/30 rounded-lg flex items-center justify-center text-emerald-400 border border-emerald-500/50 hover:bg-emerald-900/50 transition-colors">
        2번 게임
      </div>
      <div className="w-32 h-32 bg-emerald-900/30 rounded-lg flex items-center justify-center text-emerald-400 border border-emerald-500/50 hover:bg-emerald-900/50 transition-colors">
        3번 게임
      </div>
      <div className="w-32 h-32 bg-emerald-900/30 rounded-lg flex items-center justify-center text-emerald-400 border border-emerald-500/50 hover:bg-emerald-900/50 transition-colors">
        4번 게임
      </div>
    </div>
  );
}
