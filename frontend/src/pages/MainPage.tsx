import { useState, useEffect } from "react";
import { Header } from "@/pages/components/Header";
import { ChatHistory, type ChatMessage } from "@/pages/components/ChatHistory";
import { InputGameSearch } from "@/pages/components/InputGameSearch";

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

  // messages 상태 변경 시 localStorage에 저장
  useEffect(() => {
    localStorage.setItem("chatMessages", JSON.stringify(messages));
  }, [messages]);

  const handleClearChat = () => {
    setMessages([]);
    localStorage.removeItem("chatMessages");
  };

  const handleSendMessage = (query: string) => {
    // 사용자 메시지 추가
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: query,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // AI 응답 시뮬레이션 (TODO: 백엔드 API 호출)
    setIsLoading(true);
    setTimeout(() => {
      const aiMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: query,
        games: [],
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);
      setIsLoading(false);
    }, 1500);
  };

  return (
    <div className="w-full min-h-screen flex flex-col bg-slate-900 text-slate-100">
      {/* Header */}
      <div className="w-full border-b border-slate-700/50 py-3 px-6 bg-slate-800/50">
        <div className="max-w-360 mx-auto flex items-center justify-between">
          <Header />
          <button
            onClick={handleClearChat}
            className="px-3 py-1 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-colors"
          >
            ✨ New Chat
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
