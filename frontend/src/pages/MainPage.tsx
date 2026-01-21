import { useState } from "react";
import budocki from "../assets/budocki.png";

export default function MainPage() {
  const [style, setStyle] = useState<boolean>(true);

  return (
    <div className="w-full max-w-360 mx-auto px-12 min-h-screen flex flex-col text-center items-center pt-20 pb-28 gap-6">
      {/* 상단: 로고 및 인사말 */}
      <div className="w-full flex flex-col items-center">
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

        <p className="text-l text-slate-300 mb-4">
          A personalized Steam game recommendation chatbot.
        </p>

        <div className="w-50 flex items-end gap-2 justify-center bg-[#212529]">
          <input
            id="searchInput"
            type="text"
            className="w-full border-0 border-b p-1 text-center border-slate-400 outline-none text-sm text-slate-300 placeholder-slate-400"
            placeholder="Your Steam ID"
          />
          <p className="text-slate-400 text-sm">⮐</p>
        </div>

        <div className="w-full mt-10 flex gap-5 text-slate-300 p-6 bg-[#2D3338] rounded-lg shadow-lg">
          <div className="w-32 h-32 bg-slate-600 rounded-lg flex items-center justify-center">
            1번 게임
          </div>
          <div className="w-32 h-32 bg-slate-600 rounded-lg flex items-center justify-center">
            2번 게임
          </div>
          <div className="w-32 h-32 bg-slate-600 rounded-lg flex items-center justify-center">
            3번 게임
          </div>
          <div className="w-32 h-32 bg-slate-600 rounded-lg flex items-center justify-center">
            4번 게임
          </div>
        </div>
      </div>

      {/* 중단: 스타일 토글 및 추천 뷰 */}
      <div className="mt-10 text-slate-300 flex flex-col gap-6 w-full flex-1">
        {style ? (
          <button
            className="self-end text-sm text-slate-400 underline"
            onClick={() => setStyle(false)}
          >
            스타일 개선 보기
          </button>
        ) : (
          <button
            className="self-end text-sm text-slate-400 underline"
            onClick={() => setStyle(true)}
          >
            기존 스타일 보기
          </button>
        )}
        {style ? <OldRecommendationView /> : <NewRecommendationView />}
      </div>

      {/* 하단: fixed로 고정된 검색 입력 */}
      <div className="fixed bottom-0 left-0 right-0 w-full max-w-360 mx-auto px-12 flex items-end gap-5 justify-center pb-10 bg-[#212529]">
        <div className="flex flex-col w-full">
          <input
            id="searchInput"
            type="text"
            className="border-0 border-b-2 p-2 text-center border-slate-400 outline-none text-slate-300 placeholder-slate-400"
            placeholder="What kind of games are you looking for?"
          />
        </div>
        <p className="text-slate-400">⮐</p>
      </div>
    </div>
  );
}

export function OldRecommendationView() {
  return (
    <div className="p-8 flex flex-col text-start">
      🎯 당신을 위한 추천 게임 <br />
      <br />
      선호 스타일: 스토리 중심 · 싱글 플레이 · 몰입감
      <br />
      <br />
      1. 위처 3: 와일드 헌트
      <br />
      의미 있는 선택과 깊이 있는 스토리를 중심으로 한 오픈월드 RPG입니다.
      <br />
      <br />
      2. 디스코 엘리시움
      <br />
      대사와 선택이 핵심이 되는 서사 중심 RPG로, 독특한 분위기와 철학적인
      스토리가 특징입니다.
      <br />
      <br />
      3. 레드 데드 리뎀션 2<br />
      영화 같은 연출과 뛰어난 세계관으로 강한 몰입감을 주는 스토리 중심
      게임입니다.
      <br />
      <br />
      4. 하데스
      <br />
      빠른 전투와 점진적으로 전개되는 스토리가 결합된 액션 로그라이크
      게임입니다.
      <br />
      <br />
    </div>
  );
}

export function NewRecommendationView() {
  return (
    <div className="p-8 flex flex-col text-start max-h-screen overflow-y-auto w-full">
      <h2 className="text-3xl font-bold text-white mb-2">
        🎯 당신을 위한 추천 게임
      </h2>

      {/* 선호 스타일 배지 */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {["스토리 중심", "싱글 플레이", "몰입감"].map((style) => (
          <span
            key={style}
            className="px-3 py-1 bg-blue-900 text-blue-200 rounded-full text-sm"
          >
            {style}
          </span>
        ))}
      </div>

      {/* 게임 추천 카드 */}
      <div className="space-y-4">
        {[
          {
            num: 1,
            title: "위처 3: 와일드 헌트",
            desc: "의미 있는 선택과 깊이 있는 스토리를 중심으로 한 오픈월드 RPG입니다.",
            icon: "🏰",
          },
          {
            num: 2,
            title: "디스코 엘리시움",
            desc: "대사와 선택이 핵심이 되는 서사 중심 RPG로, 독특한 분위기와 철학적인 스토리가 특징입니다.",
            icon: "💭",
          },
          {
            num: 3,
            title: "레드 데드 리뎀션 2",
            desc: "영화 같은 연출과 뛰어난 세계관으로 강한 몰입감을 주는 스토리 중심 게임입니다.",
            icon: "🤠",
          },
          {
            num: 4,
            title: "하데스",
            desc: "빠른 전투와 점진적으로 전개되는 스토리가 결합된 액션 로그라이크 게임입니다.",
            icon: "⚔️",
          },
        ].map((game) => (
          <div
            key={game.num}
            className="p-4 bg-[#2D3338] rounded-lg border border-slate-600 hover:border-blue-500 hover:bg-[#374151] transition-all duration-300 cursor-pointer"
          >
            <div className="flex items-start gap-4">
              <div className="text-4xl">{game.icon}</div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-blue-400 font-bold text-lg">
                    #{game.num}
                  </span>
                  <h3 className="text-xl font-bold text-white">{game.title}</h3>
                </div>
                <p className="text-slate-300 mt-2 text-sm">{game.desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
