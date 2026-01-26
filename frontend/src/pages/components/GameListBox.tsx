'use client';

import { useState } from 'react';

export function GameListBox() {
  const [selectedGame, setSelectedGame] = useState<number | null>(null);

  const games = [
    { id: 1, name: '1번 게임' },
    { id: 2, name: '2번 게임' },
    { id: 3, name: '3번 게임' },
    { id: 4, name: '4번 게임' },
  ];

  const handleGameClick = (gameId: number) => {
    setSelectedGame(gameId);
  };

  return (
    <>
      <div className="w-full mt-6 relative">
        <div className="flex gap-5 text-emerald-300 p-6 bg-slate-800 rounded-lg shadow-lg border border-emerald-500/30">
          {games.map((game) => (
            <div
              key={game.id}
              onClick={() => handleGameClick(game.id)}
              className="w-32 h-32 bg-emerald-900/30 rounded-lg flex items-center justify-center text-emerald-400 border border-emerald-500/50 hover:bg-emerald-900/50 transition-colors cursor-pointer"
            >
              {game.name}
            </div>
          ))}
        </div>

        {selectedGame && (
          <>
            {/* 모달 오버레이 */}
            <div
              className="fixed inset-0 bg-black/50 z-50"
              onClick={() => setSelectedGame(null)}
            />
            {/* 모달 */}
            <div className="fixed inset-0 flex items-center justify-center z-50">
              <div className="w-96 p-8 bg-slate-800 rounded-lg shadow-2xl border border-emerald-500/30">
                <h2 className="text-2xl font-bold text-emerald-400 mb-4">{selectedGame}번 게임 상세설명</h2>
                <p className="text-emerald-300 mb-6">
                  게임 상세설명이 여기에 표시됩니다.
                </p>
                <button
                  onClick={() => setSelectedGame(null)}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2 px-4 rounded transition-colors"
                >
                  닫기
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
