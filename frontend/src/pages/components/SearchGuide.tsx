export function SearchGuide() {
  return (
    <div className="mb-4 mt-1 p-4 bg-slate-800 rounded-lg border-l-4 border-emerald-400 animate-fade-in-up">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">💡</span>
        <span className="text-xs text-slate-400 font-semibold">
          TailorPlay AI 가이드
        </span>
      </div>
      <p className="text-slate-300 text-sm leading-relaxed">
        당신의 게임 취향을 분석해주는 AI입니다. 찾고 싶은 게임의 장르, 특징,
        플레이 스타일 등을 자유롭게 입력해보세요. TailorPlay가 당신의 취향에
        맞는 게임들을 추천해드립니다.
      </p>
    </div>
  );
}
