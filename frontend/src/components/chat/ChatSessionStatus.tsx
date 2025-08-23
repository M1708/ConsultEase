"use client";

import { useChatSession } from "@/hooks/useChatSession";
import { formatDistanceToNow } from "date-fns";

export const ChatSessionStatus = () => {
  const { chatSessionLoading, lastSaved, saveChatSession } = useChatSession();

  return (
    <div className="flex items-center space-x-2 text-xs text-gray-500">
      {chatSessionLoading ? (
        <div className="flex items-center space-x-1">
          <div className="animate-spin rounded-full h-3 w-3 border-b border-gray-400"></div>
          <span>Saving...</span>
        </div>
      ) : lastSaved ? (
        <span>
          Last saved {formatDistanceToNow(lastSaved, { addSuffix: true })}
        </span>
      ) : (
        <span>Not saved</span>
      )}

      <button
        onClick={saveChatSession}
        disabled={chatSessionLoading}
        className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
      >
        Save now
      </button>
    </div>
  );
};
