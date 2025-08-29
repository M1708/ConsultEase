import { ChatMessage as ChatMessageType } from "@/types/chat";
import { User, Bot, Check, X, Workflow } from "lucide-react";
import { clsx } from "clsx";

interface ChatMessageProps {
  message: ChatMessageType;
}

export const ChatMessage = ({ message }: ChatMessageProps) => {
  const isUser = message.isUser;
  const content = isUser ? message.message : message.response;

  return (
    <div
      className={clsx(
        "flex gap-3 mb-4",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <div className="flex-shrink-0">
          <div className="h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center">
            <Bot className="h-4 w-4 text-blue-600" />
          </div>
        </div>
      )}

      <div className={clsx("max-w-3xl", isUser ? "order-1" : "order-2")}>
        <div
          className={clsx(
            "px-4 py-3 rounded-lg",
            isUser
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-900 border"
          )}
        >
          {!isUser && (
            <div className="flex items-center gap-2 mb-2 text-xs">
              <span className="font-medium text-gray-600">Milo</span>
              {message.success ? (
                <Check className="h-3 w-3 text-green-500" />
              ) : (
                <X className="h-3 w-3 text-red-500" />
              )}
              {message.workflow_id && (
                <Workflow className="h-3 w-3 text-purple-500" />
              )}
            </div>
          )}

          <div className="whitespace-pre-wrap">{content}</div>

          {message.data && Object.keys(message.data).length > 0 && (
            <div className="mt-2 pt-2 border-t border-gray-200">
              <details className="text-xs">
                <summary className="cursor-pointer text-gray-500 hover:text-gray-700">
                  View Details
                </summary>
                <pre className="mt-1 bg-gray-50 p-2 rounded text-xs overflow-auto">
                  {JSON.stringify(message.data, null, 2)}
                </pre>
              </details>
            </div>
          )}
        </div>

        <div
          className={clsx(
            "text-xs text-gray-500 mt-1",
            isUser ? "text-right" : "text-left"
          )}
        >
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>

      {isUser && (
        <div className="flex-shrink-0 order-2">
          <div className="h-8 w-8 bg-gray-200 rounded-full flex items-center justify-center">
            <User className="h-4 w-4 text-gray-600" />
          </div>
        </div>
      )}
    </div>
  );
};
