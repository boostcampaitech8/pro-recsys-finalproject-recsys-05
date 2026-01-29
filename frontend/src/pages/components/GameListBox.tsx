import { useState } from "react";
import type { RecommendedGame } from "@/api/gameApi";

interface GameListBoxProps {
  games?: RecommendedGame[];
  loading?: boolean;
}

export function GameListBox({ games = [], loading = false }: GameListBoxProps) {
  const [selectedGame, setSelectedGame] = useState<number | null>(null);

  const selectedGameData = games.find((game) => game.app_id === selectedGame);

  if (loading) {
    return (
      <div className="w-full mt-6 p-6 bg-slate-800 rounded-lg border border-emerald-500/30 text-center">
        <p className="text-emerald-300">로딩 중...</p>
      </div>
    );
  }

  if (games.length === 0) {
    return (
      <div className="w-full mt-6 p-6 bg-slate-800 rounded-lg border border-emerald-500/30 text-center">
        <p className="text-emerald-300">Steam ID를 입력하여 게임을 추천받으세요.</p>
      </div>
    );
  }

  return (
    <>
      <div className="w-full mt-6 relative">
        <div className="flex gap-5 text-emerald-300 p-6 bg-slate-800 rounded-lg shadow-lg border border-emerald-500/30 overflow-x-auto">
          {games.map((game) => (
            <div
              key={game.app_id}
              onClick={() => setSelectedGame(game.app_id)}
              className="flex flex-col items-center justify-center gap-2 p-3 bg-emerald-900/30 rounded-lg border border-emerald-500/50 hover:bg-emerald-900/50 transition-all duration-300 cursor-pointer group w-28 h-32 flex-shrink-0"
            >
              <div className="text-xs text-emerald-400 font-semibold">
                {game.score.toFixed(2)}
              </div>
              {game.header_image ? (
                <img
                  src={game.header_image}
                  alt={game.name}
                  className="w-20 h-16 object-cover rounded group-hover:scale-110 transition-transform"
                />
              ) : (
                <div className="text-3xl group-hover:scale-110 transition-transform">🎮</div>
              )}
              <div className="text-center">
                <h4 className="text-xs font-bold text-emerald-400 leading-tight line-clamp-2">
                  {game.name}
                </h4>
              </div>
            </div>
          ))}
        </div>

        {selectedGameData && (
          <>
            {/* 모달 오버레이 */}
            <div
              className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 animate-modal-fade-in"
              onClick={() => setSelectedGame(null)}
            />
            {/* 모달 */}
            <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
              <div className="w-full max-w-md bg-slate-800 rounded-lg shadow-2xl border border-emerald-500/30 overflow-hidden animate-modal-slide-in">
                {/* 게임 이미지 */}
                <div className="flex justify-center py-10 bg-emerald-900/20 border-b border-emerald-500/20">
                  {selectedGameData.header_image ? (
                    <img
                      src={selectedGameData.header_image}
                      alt={selectedGameData.name}
                      className="w-64 h-40 object-cover rounded"
                    />
                  ) : (
                    <div className="text-6xl">🎮</div>
                  )}
                </div>

                {/* 게임 정보 */}
                <div className="p-6 space-y-4">
                  {/* 제목 */}
                  <div>
                    <h2 className="text-2xl font-bold text-emerald-400 leading-tight">
                      {selectedGameData.name}
                    </h2>
                  </div>

                  {/* 추천 점수 */}
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold text-yellow-400">
                      ⭐ {selectedGameData.score.toFixed(4)}
                    </span>
                  </div>

                  {/* 장르 */}
                  <div className="flex flex-wrap gap-2">
                    {selectedGameData.genres_kr.map((genre, idx) => (
                      <span
                        key={idx}
                        className="text-xs font-semibold text-emerald-400 bg-emerald-900/40 px-3 py-1 rounded-full border border-emerald-500/30"
                      >
                        {genre}
                      </span>
                    ))}
                  </div>

                  {/* 설명 */}
                  <div className="pt-2">
                    <p className="text-slate-200 text-sm leading-relaxed">
                      {selectedGameData.short_description_kr}
                    </p>
                  </div>

                  {/* 가격 및 출시일 */}
                  <div className="flex justify-between text-sm text-slate-300">
                    <span>💰 {selectedGameData.price.toLocaleString()} KRW</span>
                    <span>📅 {selectedGameData.release_date}</span>
                  </div>
                </div>

                {/* 버튼 */}
                <div className="px-6 pb-6 flex gap-3">
                  <button
                    onClick={() => setSelectedGame(null)}
                    className="flex-1 bg-slate-600 hover:bg-slate-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-300"
                  >
                    닫기
                  </button>
                  <button
                    onClick={() => {
                      const url = `https://store.steampowered.com/app/${selectedGameData.app_id}`;
                      window.open(url, "_blank");
                    }}
                    className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-300"
                  >
                    Steam에서 보기
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
