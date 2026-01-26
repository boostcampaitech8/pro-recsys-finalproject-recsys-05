"use client";

import { useState } from "react";

interface Game {
  id: number;
  name: string;
  genre: string;
  description: string;
  image: string;
}

export function GameListBox() {
  const [selectedGame, setSelectedGame] = useState<number | null>(null);

  const games: Game[] = [
    {
      id: 1,
      name: "위처 3: 와일드 헌트",
      genre: "RPG",
      description:
        "오픈월드 RPG의 정점. 풍부한 스토리와 선택지, 그리고 매력적인 캐릭터들이 가득한 마스터피스입니다.",
      image: "🏰",
    },
    {
      id: 2,
      name: "디스코 엘리시움",
      genre: "RPG",
      description:
        "독특한 턴 기반 RPG로, 깊이 있는 스토리텔링과 정치, 철학을 다루는 혁신적인 게임입니다.",
      image: "💭",
    },
    {
      id: 3,
      name: "레드 데드 리뎀션 2",
      genre: "액션 어드벤처",
      description:
        "방대한 오픈월드에서 경험하는 몰입감 있는 스토리. 세세한 디테일이 살아있는 서부시대 액션 게임입니다.",
      image: "🤠",
    },
    {
      id: 4,
      name: "하데스",
      genre: "액션 로그라이크",
      description:
        "신화 속 세계관을 배경으로 한 어려운 난이도의 액션 게임. 각 플레이마다 다른 경험을 제공합니다.",
      image: "⚔️",
    },
  ];

  const selectedGameData = games.find((game) => game.id === selectedGame);

  return (
    <>
      <div className="w-full mt-6 relative">
        <div className="flex gap-5 text-emerald-300 p-6 bg-slate-800 rounded-lg shadow-lg border border-emerald-500/30">
          {games.map((game) => (
            <div
              key={game.id}
              onClick={() => setSelectedGame(game.id)}
              className="flex flex-col items-center justify-center gap-2 p-3 bg-emerald-900/30 rounded-lg border border-emerald-500/50 hover:bg-emerald-900/50 transition-all duration-300 cursor-pointer group w-28 h-32"
            >
              <div className="text-3xl group-hover:scale-110 transition-transform">
                {game.image}
              </div>
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
                  <div className="text-6xl">{selectedGameData.image}</div>
                </div>

                {/* 게임 정보 */}
                <div className="p-6 space-y-4">
                  {/* 제목 */}
                  <div>
                    <h2 className="text-2xl font-bold text-emerald-400 leading-tight">
                      {selectedGameData.name}
                    </h2>
                  </div>

                  {/* 장르 */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-emerald-400 bg-emerald-900/40 px-3 py-1 rounded-full border border-emerald-500/30">
                      {selectedGameData.genre}
                    </span>
                  </div>

                  {/* 설명 */}
                  <div className="pt-2">
                    <p className="text-slate-200 text-sm leading-relaxed">
                      {selectedGameData.description}
                    </p>
                  </div>
                </div>

                {/* 닫기 버튼 */}
                <div className="px-6 pb-6 flex gap-3">
                  <button
                    onClick={() => setSelectedGame(null)}
                    className="flex-1 bg-slate-600 hover:bg-slate-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-300"
                  >
                    닫기
                  </button>
                  <button
                    onClick={() => alert("게임 url로 이동합니다.")}
                    className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-300"
                  >
                    게임하러 가기
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
