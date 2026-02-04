export function SearchGuide() {
  return (
    <div className="flex flex-col text-start w-full gap-2 animate-fade-in-up">
      <div className="flex justify-start w-full">
        <div className="max-w-md bg-slate-700 text-slate-100 p-3 rounded-lg rounded-tl-none border border-emerald-400/50 text-sm">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">🤖</span>
            <span className="text-xs text-emerald-300 font-semibold">
              TailorPlay
            </span>
          </div>
          <p className="text-xs leading-relaxed">
            안녕하세요! 👋 저는 당신의 게임 취향을 분석해주는 AI입니다.
            <br />
            <br />
            정밀한 추천을 위해 steam_id를 입력해주세요. 찾고 싶은 게임의 장르, 특징, 플레이 스타일 등을 자유롭게 입력해보세요. 당신의 취향에 맞는 게임들을 추천해드리겠습니다.
          </p>
        </div>
      </div>
    </div>
  );
}
