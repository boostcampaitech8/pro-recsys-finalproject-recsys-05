export function InputSteamID() {
  return (
    <div className="w-50 flex items-end gap-2 justify-center bg-transparent">
      <input
        id="steamIdInput"
        type="text"
        className="w-full border-0 border-b p-1 text-center border-emerald-400 outline-none text-sm text-emerald-300 placeholder-gray-400"
        placeholder="Your Steam ID"
      />
      <p className="text-emerald-400 text-sm">⮐</p>
    </div>
  );
}
