import budocki from "@/assets/budocki.png";

export function Header() {
  return (
    <div className="w-full flex flex-col items-center">
      <img
        src={budocki}
        alt="Logo"
        className="w-14 h-auto m-auto"
        loading="lazy"
      />
      <p className="text-white mb-2">Budocki</p>
      <h1 className="text-5xl font-bold text-white mb-2">
        Welcome to TailorPlay!
      </h1>

      <p className="text-l text-gray-300 mb-4">
        A personalized Steam game recommendation chatbot.
      </p>
    </div>
  );
}
