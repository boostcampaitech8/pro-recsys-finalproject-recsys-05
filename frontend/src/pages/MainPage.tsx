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
            className="group relative px-5 py-2.5 text-sm font-semibold text-emerald-200 transition-all duration-400 rounded-lg overflow-hidden"
            style={{
              background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.08))',
              border: '1px solid rgba(16, 185, 129, 0.4)',
            }}
          >
            {/* 배경 글로우 */}
            <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-400 rounded-lg" style={{
              background: 'radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.2), transparent)',
            }}></div>

            {/* 상단 글로우 라인 */}
            <div className="absolute top-0 left-0 right-0 h-0.5 opacity-0 group-hover:opacity-100 transition-opacity duration-400" style={{
              background: 'linear-gradient(90deg, transparent, rgba(16, 185, 129, 0.6), transparent)',
            }}></div>

            {/* 텍스트 + 아이콘 */}
            <span className="relative flex items-center gap-2">
              <span className="inline-block transition-all duration-400 group-hover:scale-110 group-hover:-rotate-12">✦</span>
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
