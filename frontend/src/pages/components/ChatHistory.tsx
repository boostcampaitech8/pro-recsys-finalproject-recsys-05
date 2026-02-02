import { useEffect, useRef } from "react";
import type { RecommendedGame } from "@/api/gameApi";
import { UserMessage } from "./UserMessage";
import { LLMAnswerBox } from "./LLMAnswerBox";
import { SearchGuide } from "./SearchGuide";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  games?: RecommendedGame[];
  message?: string;
  timestamp: Date;
}

interface ChatHistoryProps {
  messages: ChatMessage[];
  isLoading?: boolean;
}

export function ChatHistory({ messages, isLoading = false }: ChatHistoryProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 스크롤을 항상 아래로 유지
    if (containerRef.current) {
      setTimeout(() => {
        containerRef.current!.scrollTop = containerRef.current!.scrollHeight;
      }, 0);
    }
  }, [messages, isLoading]);

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-2 pb-24">
      {messages.length === 0 ? (
        <div className="w-full flex items-start justify-center pt-8">
          <SearchGuide />
        </div>
      ) : (
        <>
          {messages.map((msg) =>
            msg.role === "user" ? (
              <UserMessage key={msg.id} content={msg.content} />
            ) : (
              <LLMAnswerBox
                key={msg.id}
                searchQuery={msg.content}
                games={msg.games}
                message={msg.message}
              />
            )
          )}
          {isLoading && (
            <div className="flex justify-start mb-2 animate-fade-in-up">
              <div className="bg-slate-800 p-4 rounded-lg border-l-4 border-emerald-400 flex items-center gap-2">
                <span className="text-lg">🤖</span>
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }}></div>
                  <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
