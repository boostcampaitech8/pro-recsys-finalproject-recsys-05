import { useState } from "react";
import { Header } from "@/pages/components/Header";
import { GameListBox } from "@/pages/components/GameListBox";
import { LLMAnswerBox } from "@/pages/components/LLMAnswerBox";
import { InputGameSearch } from "@/pages/components/InputGameSearch";

export default function MainPage() {
  const [hasSearched, setHasSearched] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [showAnswerBox, setShowAnswerBox] = useState(true);

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setHasSearched(true);
    setShowAnswerBox(true);
  };

  const handleCloseAnswerBox = () => {
    setShowAnswerBox(false);
  };

  return (
    <div className="w-full min-h-screen flex flex-col bg-slate-900 text-emerald-300">
      <div className="w-full bg-linear-to-b from-emerald-900/40 to-slate-900/20 py-20 text-center">
        <Header />
      </div>
      <div className="w-full max-w-360 mx-auto px-12 flex flex-col text-center items-center pb-28 gap-6">
        <GameListBox />

        <div className="w-full mt-auto">
          {hasSearched && showAnswerBox && <LLMAnswerBox searchQuery={searchQuery} onClose={handleCloseAnswerBox} />}
          <InputGameSearch onSearch={handleSearch} />
        </div>
      </div>
    </div>
  );
}