import { useState, useEffect } from "react";
import { Header } from "@/pages/components/Header";
import { ChatHistory, type ChatMessage } from "@/pages/components/ChatHistory";
import { InputGameSearch } from "@/pages/components/InputGameSearch";
import { FloatingGameButton } from "@/components/game/FloatingGameButton";
import { GameModal } from "@/components/game/GameModal";
import { GameFlapperGame } from "@/components/game/GameFlapperGame";
import { sendChatMessage } from "@/api/userApi";
import {
  getUserId,
  setUserId,
  getSteamId,
  setSteamId,
} from "@/utils/userStorage";

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

type SteamIdStatus =
  | "not_collected"
  | "valid"
  | "invalid_ask_retry"
  | "skipped";

export default function MainPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(loadChatHistory);
  const [isLoading, setIsLoading] = useState(false);
  const [isGameOpen, setIsGameOpen] = useState(false);
  const [steamIdStatus, setSteamIdStatus] = useState<SteamIdStatus>(() => {
    return getSteamId() ? "valid" : "not_collected";
  });

  // messages 상태 변경 시 localStorage에 저장
  useEffect(() => {
    localStorage.setItem("chatMessages", JSON.stringify(messages));
  }, [messages]);

  const validateSteamId = (steamId: string): boolean => {
    // Steam ID는 17자리 숫자로 구성됨
    const steamIdRegex = /^\d{17}$/;
    return steamIdRegex.test(steamId.trim());
  };

  const handleClearChat = () => {
    setMessages([]);
    localStorage.removeItem("chatMessages");
    localStorage.removeItem("steam_id");
    setSteamIdStatus("not_collected");
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
      // Case 1: Steam ID 수집 중
      if (steamIdStatus === "not_collected") {
        const isValid = validateSteamId(query);

        if (isValid) {
          setSteamId(query.trim());
          setSteamIdStatus("valid");
          const aiMessage: ChatMessage = {
            id: (Date.now() + 1).toString(),
            role: "assistant",
            content: query,
            message: "이 아이디를 통해 user의 게임 리스트와 정보를 불러옵니다.",
            games: [],
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, aiMessage]);
        } else {
          setSteamIdStatus("invalid_ask_retry");
          const aiMessage: ChatMessage = {
            id: (Date.now() + 1).toString(),
            role: "assistant",
            content: query,
            message:
              "올바른 Steam ID 형식이 아닙니다. Steam ID는 17자리 숫자입니다. 재입력하시겠습니까? (예/아니오)",
            games: [],
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, aiMessage]);
        }
        setIsLoading(false);
        return;
      }

      // Case 2: 재입력 여부 질문 중
      if (steamIdStatus === "invalid_ask_retry") {
        const answer = query.trim().toLowerCase();
        // 긍정 답변 체크 (예, 응, 네, yes, y, ㅇㅇ 등)
        const isPositive = [
          "예",
          "응",
          "네",
          "yes",
          "y",
          "ㅇㅇ",
          "ㅇ",
        ].includes(answer);

        if (isPositive) {
          setSteamIdStatus("not_collected");
          const aiMessage: ChatMessage = {
            id: (Date.now() + 1).toString(),
            role: "assistant",
            content: query,
            message: "Steam ID를 다시 입력해주세요.",
            games: [],
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, aiMessage]);
        } else {
          setSteamIdStatus("skipped");
          const aiMessage: ChatMessage = {
            id: (Date.now() + 1).toString(),
            role: "assistant",
            content: query,
            message:
              "steamid가 없어도 서비스 이용 가능합니다. 원하시는 게임을 물어보세요.",
            games: [],
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, aiMessage]);
        }
        setIsLoading(false);
        return;
      }

      // Case 3: 정상 API 통신 (steamIdStatus === 'valid' 또는 'skipped')
      const userId = getUserId();
      const steamId = getSteamId();
      const response = await sendChatMessage({
        content: query,
        user_id: userId,
        steam_id: steamId,
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
