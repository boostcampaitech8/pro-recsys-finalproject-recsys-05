import { useState, useRef, useEffect } from "react";

interface InputGameSearchProps {
  onSearch?: (query: string) => void | Promise<void>;
  isLoading?: boolean;
}

export function InputGameSearch({
  onSearch,
  isLoading = false,
}: InputGameSearchProps) {
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!isLoading) {
      inputRef.current?.focus();
    }
  }, [isLoading]);

  const handleSearch = async () => {
    if (input.trim()) {
      await onSearch?.(input);
      setInput("");
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !isLoading) {
      void handleSearch();
    }
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 w-full bg-slate-900 z-40 px-24">
      <div className="w-full max-w-360 mx-auto px-6 flex items-end gap-3 justify-center pb-6">
        <div className="flex flex-col w-full">
          <input
            ref={inputRef}
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
          onClick={() => void handleSearch()}
          disabled={isLoading || !input.trim()}
          className="text-emerald-400 hover:text-emerald-300 transition-colors cursor-pointer disabled:opacity-50 text-lg"
        >
          ⮐
        </button>
      </div>
    </div>
  );
}
