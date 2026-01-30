import { useState } from "react";
import type { RecommendedGame } from "@/api/gameApi";

interface LLMAnwerBoxProps {
  searchQuery: string;
  games?: RecommendedGame[];
  message?: string;
}

export function LLMAnswerBox({ searchQuery, games }: LLMAnwerBoxProps) {
  const [selectedGame, setSelectedGame] = useState<RecommendedGame | null>(null);
  // TODO: searchQuery를 백엔드 API 호출에 사용할 예정
  console.log("Search query:", searchQuery);

  const emojis = ["🏰", "💭", "🤠", "⚔️"];
  const hasGames = games && games.length > 0;

  return (
    <div className="flex flex-col text-start w-full gap-2 animate-fade-in-up">
      {/* LLM 답변 말풍선 */}
      <div className="flex justify-start">
        <div className="max-w-xs bg-slate-700 text-slate-100 p-3 rounded-lg rounded-tl-none border border-emerald-400/50 text-sm">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">🤖</span>
            <span className="text-xs text-emerald-300 font-semibold">
              AI 분석 결과
            </span>
          </div>
          <p className="text-xs leading-relaxed">
            당신의 플레이 스타일을 분석한 결과,{" "}
            <span className="text-emerald-300 font-semibold">
              깊이 있는 스토리
            </span>
            와{" "}
            <span className="text-emerald-300 font-semibold">
              싱글 플레이 경험
            </span>
            을 중시하는 것으로 보입니다. 이러한 취향에 맞는 게임들을 추천드립니다.
          </p>
        </div>
      </div>

      {/* 추천 게임 박스 (가로 스크롤) - 게임이 있을 때만 표시 */}
      {hasGames && (
        <div className="mt-2 pt-3 border-t border-slate-700/50">
          <div className="flex gap-3 overflow-x-auto pb-2">
            {games.map((game, index) => (
              <div
                key={game.app_id}
                onClick={() => setSelectedGame(game)}
                className="flex flex-col items-center justify-center gap-2 p-3 bg-slate-600 rounded-lg hover:brightness-110 transition-all duration-300 cursor-pointer group shrink-0 w-24"
              >
                <div className="text-3xl group-hover:scale-110 transition-transform">
                  {game.header_image ? (
                    <img
                      src={game.header_image}
                      alt={game.name}
                      className="w-16 h-12 object-cover rounded"
                    />
                  ) : (
                    emojis[index % emojis.length]
                  )}
                </div>
                <div className="text-center">
                  <h4 className="text-xs font-bold text-white leading-tight line-clamp-2">
                    {game.name}
                  </h4>
                  <p className="text-xs text-slate-300 mt-0.5">
                    ⭐ {game.score.toFixed(1)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 게임 상세 모달 */}
      {selectedGame && (
        <>
          <div
            className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50"
            onClick={() => setSelectedGame(null)}
          />
          <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
            <div className="w-full max-w-md bg-slate-800 rounded-lg shadow-2xl border border-emerald-500/30 overflow-hidden animate-fade-in-up">
              {/* 게임 이미지 */}
              <div className="flex justify-center py-10 bg-emerald-900/20 border-b border-emerald-500/20">
                {selectedGame.header_image ? (
                  <img
                    src={selectedGame.header_image}
                    alt={selectedGame.name}
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
                    {selectedGame.name}
                  </h2>
                </div>

                {/* 추천 점수 */}
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold text-yellow-400">
                    ⭐ {selectedGame.score.toFixed(2)}
                  </span>
                </div>

                {/* 장르 */}
                <div className="flex flex-wrap gap-2">
                  {selectedGame.genres_kr.map((genre, idx) => (
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
                    {selectedGame.short_description_kr}
                  </p>
                </div>

                {/* 가격 및 출시일 */}
                <div className="flex justify-between text-sm text-slate-300">
                  <span>💰 {selectedGame.price.toLocaleString()} KRW</span>
                  <span>📅 {selectedGame.release_date}</span>
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
                    const url = `https://store.steampowered.com/app/${selectedGame.app_id}`;
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
  );
}
