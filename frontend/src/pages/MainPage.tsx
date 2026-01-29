import { useState, useEffect } from "react";
import { Header } from "@/pages/components/Header";
import { GameListBox } from "@/pages/components/GameListBox";
import { InputGameSearch } from "@/pages/components/InputGameSearch";
import { getGameRecommendations } from "@/api/gameApi";
import type { RecommendedGame } from "@/api/gameApi";

export default function MainPage() {
  const [recommendedGames, setRecommendedGames] = useState<RecommendedGame[]>(
    [],
  );
  const [loading, setLoading] = useState(true);

  // 1단계: 마운트될 때 localStorage에서 Steam ID 읽기
  useEffect(() => {
    const savedSteamId = localStorage.getItem("steamId");

    if (!savedSteamId) {
      console.log("Steam ID를 찾을 수 없습니다. 다시 설정해주세요.");
      setLoading(false);
      return;
    }

    // 3단계: API 호출 함수
    const fetchRecommendations = async (id: string) => {
      setLoading(true);

      try {
        const data = await getGameRecommendations({
          steamid: id,
          top_k: 10,
        });
        setRecommendedGames(data.recommended_games);
        console.log(`✅ ${data.recommended_games.length}개의 게임 추천 완료`);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "알 수 없는 오류";
        console.error("❌ API 호출 실패:", errorMessage);
      } finally {
        setLoading(false);
      }
    };

    // 2단계: Steam ID가 있으면 자동으로 API 호출
    void fetchRecommendations(savedSteamId);
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
