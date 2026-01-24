import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Header } from "@/pages/components/Header";

export default function Onboarding() {
  const navigate = useNavigate();
  const [genre, setGenre] = useState("");
  const [tags, setTags] = useState("");
  const [os, setOS] = useState("");

  const handleContinue = () => {
    void navigate("/main");
  };

  return (
    <div className="w-full min-h-screen bg-slate-900 text-emerald-300">
      <div className="w-full bg-linear-to-b from-emerald-900/40 to-slate-900/20 py-20 text-center">
        <Header />
      </div>

      {/* Content Section */}
      <div className="w-full px-6 py-10">
        <div className="max-w-2xl mx-auto">
          {/* Input Cards */}
          <div className="space-y-6">
            {/* Steam ID Input */}
            <div className="bg-slate-800/50 border border-emerald-500/30 rounded-lg p-6 hover:border-emerald-500/60 transition-colors">
              <label className="block text-lg font-bold text-emerald-300 mb-4">
                Steam ID
              </label>
              <input
                type="text"
                placeholder="Steam ID 입력"
                className="w-full bg-slate-900/50 border border-emerald-500/50 rounded px-4 py-3 text-emerald-300 placeholder-emerald-600/50 outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400/30 transition font-semibold"
              />
            </div>
            {/* Genre Card */}
            <div className="bg-slate-800/50 border border-emerald-500/30 rounded-lg p-6 hover:border-emerald-500/60 transition-colors">
              <label className="block text-lg font-bold text-emerald-300 mb-4">
                선호하는 장르
              </label>
              <input
                type="text"
                value={genre}
                onChange={(e) => setGenre(e.target.value)}
                placeholder="예: RPG, FPS, 전략 게임"
                className="w-full bg-slate-900/50 border border-emerald-500/50 rounded px-4 py-2 text-emerald-300 placeholder-emerald-600/50 outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400/30 transition"
              />
            </div>

            {/* Tags Card */}
            <div className="bg-slate-800/50 border border-emerald-500/30 rounded-lg p-6 hover:border-emerald-500/60 transition-colors">
              <label className="block text-lg font-bold text-emerald-300 mb-4">
                관심 태그
              </label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="예: 멀티플레이, 인디게임, 싱글플레이"
                className="w-full bg-slate-900/50 border border-emerald-500/50 rounded px-4 py-2 text-emerald-300 placeholder-emerald-600/50 outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400/30 transition"
              />
            </div>

            {/* OS Card */}
            <div className="bg-slate-800/50 border border-emerald-500/30 rounded-lg p-6 hover:border-emerald-500/60 transition-colors">
              <label className="block text-lg font-bold text-emerald-300 mb-4">
                사용 OS
              </label>
              <input
                type="text"
                value={os}
                onChange={(e) => setOS(e.target.value)}
                placeholder="예: Windows, Mac, Linux"
                className="w-full bg-slate-900/50 border border-emerald-500/50 rounded px-4 py-2 text-emerald-300 placeholder-emerald-600/50 outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400/30 transition"
              />
            </div>
          </div>

          {/* Submit Button */}
          <button
            onClick={handleContinue}
            className="w-full mt-10 bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 px-6 rounded-lg transition-colors"
          >
            계속하기
          </button>
        </div>
      </div>
    </div>
  );
}
