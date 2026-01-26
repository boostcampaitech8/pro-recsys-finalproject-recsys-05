import { useState } from "react";
import { SearchGuide } from "./SearchGuide";
import { LLMAnswerBox } from "./LLMAnswerBox";

interface InputGameSearchProps {
  onSearch?: (query: string) => void;
}

export function InputGameSearch({ onSearch }: InputGameSearchProps) {
  const [input, setInput] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [showAnswerBox, setShowAnswerBox] = useState(false);

  const handleSearch = () => {
    if (input.trim()) {
      setSearchQuery(input);
      setShowAnswerBox(true);
      onSearch?.(input);
      setInput("");
      setIsFocused(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  return (
    <div className="mt-auto px-12">
      {(showAnswerBox || isFocused) && (
        <>
          <div className="fixed inset-0 bg-black/50 z-20" />
          <div className="fixed bottom-28 left-0 right-0 w-full max-w-360 mx-auto px-12 z-40 flex flex-col gap-2 max-h-[60vh] overflow-y-auto">
            {showAnswerBox && (
              <LLMAnswerBox
                searchQuery={searchQuery}
              />
            )}
            {isFocused && <SearchGuide />}
          </div>
        </>
      )}

      <div
        className={`fixed bottom-0 left-0 right-0 w-full max-w-360 mx-auto px-12 flex items-end gap-5 justify-center pb-10 z-40 ${showAnswerBox || isFocused ? "bg-transparent" : "bg-slate-900"}`}
      >
        <div className="flex flex-col w-full">
          <input
            id="searchInput"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            onFocus={() => {
              setIsFocused(true);
            }}
            onBlur={() => {
              setIsFocused(false);
              setShowAnswerBox(false);
            }}
            className="border-0 border-b-2 p-2 text-center border-emerald-400 outline-none text-emerald-300 placeholder-gray-400"
            placeholder="What kind of games are you looking for?"
          />
        </div>

        <button
          onClick={handleSearch}
          className="text-emerald-400 hover:text-emerald-300 transition-colors cursor-pointer"
        >
          ⮐
        </button>
      </div>
    </div>
  );
}
