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
    <div className="w-full max-w-360 mx-auto px-12 min-h-screen flex flex-col text-center items-center pt-20 pb-28 gap-6 bg-slate-900 text-emerald-300">
      <Header />
      <GameListBox />

      <div className="w-full mt-auto">
        {hasSearched && showAnswerBox && <LLMAnswerBox searchQuery={searchQuery} onClose={handleCloseAnswerBox} />}
        <InputGameSearch onSearch={handleSearch} />
      </div>
    </div>
  );
}