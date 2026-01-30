import { useState } from "react";

interface InputGameSearchProps {
  onSearch?: (query: string) => void;
  isLoading?: boolean;
}

export function InputGameSearch({ onSearch, isLoading = false }: InputGameSearchProps) {
  const [input, setInput] = useState("");

  const handleSearch = () => {
    if (input.trim()) {
      onSearch?.(input);
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !isLoading) {
      handleSearch();
    }
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 w-full max-w-360 mx-auto px-6 flex items-end gap-3 justify-center pb-6 z-40 bg-slate-900 border-t border-slate-700/50">
      <div className="flex flex-col w-full">
        <input
          id="searchInput"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          className="border-0 border-b-2 p-2 text-center border-emerald-400 outline-none text-emerald-300 placeholder-gray-400 disabled:opacity-50 bg-transparent"
          placeholder="What kind of games are you looking for?"
        />
      </div>

      <button
        onClick={handleSearch}
        disabled={isLoading || !input.trim()}
        className="text-emerald-400 hover:text-emerald-300 transition-colors cursor-pointer disabled:opacity-50 text-lg"
      >
        ⮐
      </button>
    </div>
  );
}
