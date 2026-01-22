import { useState } from "react";

interface LLMAnwerBoxProps {
  searchQuery: string;
  onClose: () => void;
}

export function LLMAnswerBox({ searchQuery, onClose }: LLMAnwerBoxProps) {
  const [isClosing, setIsClosing] = useState(false);

  // TODO: searchQuery를 백엔드 API 호출에 사용할 예정
  console.log("Search query:", searchQuery);

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      onClose();
    }, 300);
  };

  const games = [
    {
      num: 1,
      title: "위처 3: 와일드 헌트",
      image: "🏰",
      genre: "RPG",
    },
    {
      num: 2,
      title: "디스코 엘리시움",
      image: "💭",
      genre: "RPG",
    },
    {
      num: 3,
      title: "레드 데드 리뎀션 2",
      image: "🤠",
      genre: "액션 어드벤처",
    },
    {
      num: 4,
      title: "하데스",
      image: "⚔️",
      genre: "액션 로그라이크",
    },
  ];

  return (
    <div className={`flex flex-col text-start max-h-screen overflow-y-auto w-full gap-4 ${isClosing ? "animate-fade-out-down" : "animate-fade-in-up"}`}>
      {/* LLM 답변 */}
      <div className="bg-slate-800 p-4 rounded-lg border-l-4 border-emerald-400">
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-lg">🤖</span>
            <span className="text-xs text-slate-400 font-semibold">
              TailorPlay AI 분석 결과
            </span>
          </div>
          <button
            onClick={handleClose}
            className="text-emerald-500 hover:text-emerald-300 transition-colors cursor-pointer text-2xl rotate-180 mr-2"
            aria-label="Close"
          >
            ⌃
          </button>
        </div>
        <div className="space-y-2">
          <p className="text-slate-200 text-sm leading-relaxed">
            당신의 게임 히스토리와 플레이 스타일을 분석한 결과,{" "}
            <span className="text-emerald-400 font-semibold">
              깊이 있는 스토리
            </span>
            와{" "}
            <span className="text-emerald-400 font-semibold">
              싱글 플레이 경험
            </span>
            을 중시하는 것으로 보입니다.
          </p>
          <p className="text-slate-200 text-sm leading-relaxed">
            당신이 플레이한 게임들의 플레이타임 패턴과 평점 데이터를 종합하면,
            선형적인 스토리텔링보다는 선택지가 있는 플롯, 그리고 싱글플레이로
            충분히 즐길 수 있는 환경을 선호하는 것으로 판단됩니다.
          </p>
          <p className="text-slate-200 text-sm leading-relaxed">
            이러한 취향 분석을 바탕으로 아래의 게임들을 추천드립니다. 각 게임은
            당신의{" "}
            <span className="text-emerald-400 font-semibold">
              '스토리 중심, 싱글 플레이, 몰입감'
            </span>{" "}
            취향을 만족시킬 수 있는 작품들입니다.
          </p>
        </div>

        {/* 추천 게임 박스 (가로 스크롤) */}
        <div className="mt-4 pt-4 border-t border-slate-700">
          <div className="flex gap-3 overflow-x-auto pb-2">
            {games.map((game) => (
              <div
                key={game.num}
                className="flex flex-col items-center justify-center gap-2 p-3 bg-slate-600 rounded-lg hover:brightness-110 transition-all duration-300 cursor-pointer group shrink-0 w-24"
              >
                <div className="text-3xl group-hover:scale-110 transition-transform">
                  {game.image}
                </div>
                <div className="text-center">
                  <h4 className="text-xs font-bold text-white leading-tight line-clamp-2">
                    {game.title}
                  </h4>
                  <p className="text-xs text-slate-400 mt-0.5">{game.genre}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
