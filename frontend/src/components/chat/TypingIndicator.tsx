export const TypingIndicator = () => {
  return (
    <div className="flex gap-3 mb-4">
      <div className="flex-shrink-0">
        <div className="h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center">
          <Bot className="h-4 w-4 text-blue-600" />
        </div>
      </div>

      <div className="bg-gray-100 px-4 py-3 rounded-lg border">
        <div className="flex items-center gap-1">
          <div className="flex gap-1">
            <div
              className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: "0ms" }}
            />
            <div
              className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: "150ms" }}
            />
            <div
              className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: "300ms" }}
            />
          </div>
          <span className="text-sm text-gray-500 ml-2">AI is thinking...</span>
        </div>
      </div>
    </div>
  );
};
