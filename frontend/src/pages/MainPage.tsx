import { useState, useEffect } from "react";
import { Header } from "@/pages/components/Header";
import { ChatHistory, type ChatMessage } from "@/pages/components/ChatHistory";
import { InputGameSearch } from "@/pages/components/InputGameSearch";
import { FloatingGameButton } from "@/components/game/FloatingGameButton";
import { GameModal } from "@/components/game/GameModal";
import { GameFlapperGame } from "@/components/game/GameFlapperGame";
import { sendChatMessage } from "@/api/userApi";
import { getUserId, setUserId } from "@/utils/userStorage";

const loadChatHistory = (): ChatMessage[] => {
  const savedMessages = localStorage.getItem("chatMessages");
  if (savedMessages) {
    try {
      const parsed = JSON.parse(savedMessages) as ChatMessage[];
      // Date 객체 복원
      return parsed.map((msg) => ({
        ...msg,
        timestamp: new Date(msg.timestamp),
      }));
    } catch (err) {
      console.error("채팅 히스토리 로드 실패:", err);
    }
  }
  return [];
};

export default function MainPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(loadChatHistory);
  const [isLoading, setIsLoading] = useState(false);
  const [isGameOpen, setIsGameOpen] = useState(false);

  // messages 상태 변경 시 localStorage에 저장
  useEffect(() => {
    localStorage.setItem("chatMessages", JSON.stringify(messages));
  }, [messages]);

  const handleClearChat = () => {
    setMessages([]);
    localStorage.removeItem("chatMessages");
  };

  const handleSendMessage = async (query: string) => {
    // 사용자 메시지 추가
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: query,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // AI 응답 요청
    setIsLoading(true);

    try {
      const userId = getUserId();
      const response = await sendChatMessage({
        content: query,
        user_id: userId,
      });

      // user_id가 null이었으면 응답에서 온 user_id 저장
      if (!userId && response.user_id) {
        setUserId(response.user_id);
      }

      // AI 응답 메시지 추가
      const aiMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: query,
        message: response.text,
        games: [],
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      // 에러 메시지 추가 (사용자 메시지는 유지)
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: query,
        message: "AI 응답 실패: 요청을 처리하는 중 오류가 발생했습니다.",
        games: [],
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      console.error("Chat API Error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full min-h-screen flex flex-col bg-slate-900 text-slate-100">
      {/* Game Easter Egg */}
      <FloatingGameButton onClick={() => setIsGameOpen(true)} />
      <GameModal isOpen={isGameOpen} onClose={() => setIsGameOpen(false)}>
        <GameFlapperGame />
      </GameModal>

      {/* Header */}
      <div className="sticky top-0 z-50 w-full border-b border-slate-700 py-3 px-6 bg-slate-800">
        <div className="max-w-360 mx-auto flex items-center justify-between">
          <Header />
          <button
            onClick={handleClearChat}
            className="group relative px-5 py-2.5 text-sm font-semibold text-emerald-200 transition-all duration-400 rounded-lg overflow-hidden"
            style={{
              background:
                "linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.08))",
              border: "1px solid rgba(16, 185, 129, 0.4)",
              animation: "none",
            }}
          >
            {/* 배경 글로우 */}
            <div
              className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-400 rounded-lg"
              style={{
                background:
                  "radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.2), transparent)",
              }}
            ></div>

            {/* 상단 글로우 라인 */}
            <div
              className="absolute top-0 left-0 right-0 h-0.5 opacity-0 group-hover:opacity-100 transition-opacity duration-400"
              style={{
                background:
                  "linear-gradient(90deg, transparent, rgba(16, 185, 129, 0.6), transparent)",
              }}
            ></div>

            {/* 텍스트 + 아이콘 */}
            <span className="relative flex items-center gap-2">
              <span className="inline-block transition-all duration-400 group-hover:scale-110 group-hover:-rotate-12">
                ✦
              </span>
              New Chat
            </span>
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="w-full flex flex-col flex-1 items-center">
        <div className="w-full max-w-360 flex flex-col flex-1">
          {/* 채팅 히스토리 */}
          <ChatHistory messages={messages} isLoading={isLoading} />

          {/* 채팅 입력 */}
          <InputGameSearch onSearch={handleSendMessage} isLoading={isLoading} />
        </div>
      </div>
    </div>
  );
}
