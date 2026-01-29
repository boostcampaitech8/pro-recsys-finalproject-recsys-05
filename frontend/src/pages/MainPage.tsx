import { useState, useEffect } from "react";
import { Header } from "@/pages/components/Header";
import { GameListBox } from "@/pages/components/GameListBox";
import { InputGameSearch } from "@/pages/components/InputGameSearch";
import type { RecommendedGame } from "@/api/gameApi";

export default function MainPage() {
  const [recommendedGames, setRecommendedGames] = useState<RecommendedGame[]>(
    [],
  );
  const [loading, setLoading] = useState(true);

  // localStorage에 저장된 추천 게임 데이터 로드
  useEffect(() => {
    const savedGames = localStorage.getItem("recommendedGames");

    if (savedGames) {
      try {
        const games = JSON.parse(savedGames);
        setRecommendedGames(games);
        console.log(`✅ 저장된 ${games.length}개의 게임 추천 데이터 로드 완료`);
      } catch (err) {
        console.error("❌ 저장된 데이터 파싱 실패:", err);
      }
    } else {
      console.log("저장된 추천 게임 데이터가 없습니다. Onboarding을 다시 완료해주세요.");
    }

    setLoading(false);
  }, []);

  return (
    <div className="w-full max-w-360 mx-auto min-h-screen flex flex-col text-center items-center pb-22 gap-6 bg-slate-900 text-emerald-300">
      <div className="w-full bg-linear-to-b from-emerald-900/40 to-slate-900/20 py-20 text-center">
        <Header />
      </div>

      {/* contents view */}
      <div className="w-full px-12 flex flex-col text-center items-center">
        <GameListBox games={recommendedGames} loading={loading} />
      </div>
      <InputGameSearch />
    </div>
  );
}
