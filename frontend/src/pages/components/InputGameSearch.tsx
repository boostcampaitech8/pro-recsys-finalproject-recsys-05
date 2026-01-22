import { useState } from "react";
import { SearchGuide } from "./SearchGuide";

interface InputGameSearchProps {
  onSearch: (query: string) => void;
}

export function InputGameSearch({ onSearch }: InputGameSearchProps) {
  const [input, setInput] = useState("");
  const [isFocused, setIsFocused] = useState(false);

  const handleSearch = () => {
    if (input.trim()) {
      onSearch(input);
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
    <>
      {isFocused && <SearchGuide />}
      <div className="fixed bottom-0 left-0 right-0 w-full max-w-360 mx-auto px-12 flex items-end gap-5 justify-center pb-10 bg-slate-900">
        <div className="flex flex-col w-full">
          <input
            id="searchInput"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            onFocus={() => {setIsFocused(true)}}
            onBlur={() => setIsFocused(false)}
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
    </>
  );
}
