import { Header } from "@/pages/components/Header";
import { GameListBox } from "@/pages/components/GameListBox";
import { InputGameSearch } from "@/pages/components/InputGameSearch";

export default function MainPage() {
  return (
    <div className="w-full max-w-360 mx-auto min-h-screen flex flex-col text-center items-center pb-22 gap-6 bg-slate-900 text-emerald-300">
      <div className="w-full bg-linear-to-b from-emerald-900/40 to-slate-900/20 py-20 text-center">
        <Header />
      </div>

      {/* contents view */}
      <div className="w-full px-12 flex flex-col text-center items-center">
        <GameListBox />
      </div>

      <InputGameSearch />
    </div>
  );
}
