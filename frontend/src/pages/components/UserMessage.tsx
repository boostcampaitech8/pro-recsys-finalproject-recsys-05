interface UserMessageProps {
  content: string;
}

export function UserMessage({ content }: UserMessageProps) {
  return (
    <div className="flex justify-end w-full animate-fade-in-up">
      <div className="bg-emerald-600 text-white p-3 rounded-lg rounded-br-none max-w-md break-words">
        <p className="text-sm leading-relaxed">{content}</p>
      </div>
    </div>
  );
}
