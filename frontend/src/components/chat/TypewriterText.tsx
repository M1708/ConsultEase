"use client";

import { useState, useEffect, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

interface TypewriterTextProps {
  text: string;
  speed?: number; // milliseconds per character
  onComplete?: () => void;
  className?: string;
  style?: React.CSSProperties;
  enableMarkdown?: boolean; // New prop to enable/disable Markdown rendering
}

// Function to preprocess URLs for typewriter display (shows only shortened text)
const preprocessUrlsForTypewriter = (text: string): string => {
  const urlRegex = /(https?:\/\/[^\s\)\]\}]+\/?)/g;
  
  return text.replace(urlRegex, (url) => {
    // Show only shortened display text during typewriter effect
    return url.length > 50 ? `${url.substring(0, 47)}...` : url;
  });
};

// Function to preprocess URLs for final Markdown rendering
const preprocessUrlsForMarkdown = (text: string): string => {
  const urlRegex = /(https?:\/\/[^\s\)\]\}]+\/?)/g;
  
  return text.replace(urlRegex, (url) => {
    // Convert URL to Markdown link format with shortened display text
    const displayText = url.length > 50 ? `${url.substring(0, 47)}...` : url;
    return `[${displayText}](${url})`;
  });
};

export const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  speed = 10, // Reduced from 30ms to 10ms for faster typing
  onComplete,
  className = "",
  style,
  enableMarkdown = true // Default to true for Markdown support
}) => {
  const [displayedText, setDisplayedText] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);
  
  // Preprocess URLs for typewriter effect (shows shortened text only)
  const typewriterText = useMemo(() => {
    return enableMarkdown ? preprocessUrlsForTypewriter(text) : text;
  }, [text, enableMarkdown]);
  
  // Preprocess URLs for final Markdown rendering
  const markdownText = useMemo(() => {
    return enableMarkdown ? preprocessUrlsForMarkdown(text) : text;
  }, [text, enableMarkdown]);
  
  useEffect(() => {
    if (currentIndex < typewriterText.length) {
      const timer = setTimeout(() => {
        const newIndex = currentIndex + 1;
        const textToShow = typewriterText.substring(0, newIndex);
        setDisplayedText(textToShow);
        setCurrentIndex(newIndex);
      }, speed);

      return () => clearTimeout(timer);
    } else if (onComplete) {
      onComplete();
    }
  }, [currentIndex, typewriterText, speed, onComplete]);

  // Reset when text changes
  useEffect(() => {
    setDisplayedText("");
    setCurrentIndex(0);
  }, [text]);

  return (
    <div className={`whitespace-pre-wrap ${className}`} style={style}>
      {enableMarkdown ? (
        <div 
          className="max-w-none [&_*]:!m-0 [&_*]:!p-0 [&_h1]:!mb-0.5 [&_h2]:!mb-0.5 [&_h3]:!mb-0.5 [&_h4]:!mb-0.5 [&_h5]:!mb-0.5 [&_h6]:!mb-0.5 [&_p]:!m-0 [&_p]:!p-0" 
          style={{
            lineHeight: '1.2',
            margin: 0,
            padding: 0
          }}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
            components={{
              // Custom link component to ensure proper URL handling
              a: ({ href, children, ...props }) => (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 underline break-all"
                  style={{ margin: 0, padding: 0, lineHeight: '1.2' }}
                  {...props}
                >
                  {children}
                </a>
              ),
              // Custom code component for better styling
              code: ({ className, children, ...props }) => {
                const match = /language-(\w+)/.exec(className || '');
                return match ? (
                  <code className={`${className} bg-gray-100 px-1 py-0.5 rounded text-sm`} style={{ margin: 0, lineHeight: '1.2' }} {...props}>
                    {children}
                  </code>
                ) : (
                  <code className="bg-gray-100 px-1 py-0.5 rounded text-sm" style={{ margin: 0, lineHeight: '1.2' }} {...props}>
                    {children}
                  </code>
                );
              },
              // Custom pre component for code blocks
              pre: ({ children, ...props }) => (
                <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto" style={{ margin: 0, lineHeight: '1.2' }} {...props}>
                  {children}
                </pre>
              ),
              // Custom table components
              table: ({ children, ...props }) => (
                <div className="overflow-x-auto">
                  <table className="min-w-full border-collapse border border-gray-300" style={{ margin: 0, lineHeight: '1.2' }} {...props}>
                    {children}
                  </table>
                </div>
              ),
              th: ({ children, ...props }) => (
                <th className="border border-gray-300 px-4 py-2 bg-gray-50 font-semibold text-left" style={{ margin: 0, lineHeight: '1.2' }} {...props}>
                  {children}
                </th>
              ),
              td: ({ children, ...props }) => (
                <td className="border border-gray-300 px-4 py-2" style={{ margin: 0, lineHeight: '1.2' }} {...props}>
                  {children}
                </td>
              ),
              // Custom paragraph component with minimal spacing
              p: ({ children, ...props }) => (
                <p style={{ margin: 0, padding: 0, lineHeight: '1.2' }} {...props}>
                  {children}
                </p>
              ),
              // Custom heading components with minimal spacing
              h1: ({ children, ...props }) => (
                <h1 className="text-lg font-bold" style={{ margin: 0, padding: 0, lineHeight: '1.1', marginBottom: '2px' }} {...props}>
                  {children}
                </h1>
              ),
              h2: ({ children, ...props }) => (
                <h2 className="text-base font-bold" style={{ margin: 0, padding: 0, lineHeight: '1.1', marginBottom: '2px' }} {...props}>
                  {children}
                </h2>
              ),
              h3: ({ children, ...props }) => (
                <h3 className="text-sm font-bold" style={{ margin: 0, padding: 0, lineHeight: '1.1', marginBottom: '2px' }} {...props}>
                  {children}
                </h3>
              ),
              // Custom list components with minimal spacing
              ul: ({ children, ...props }) => (
                <ul className="pl-4" style={{ margin: 0, padding: 0, lineHeight: '1.2' }} {...props}>
                  {children}
                </ul>
              ),
              ol: ({ children, ...props }) => (
                <ol style={{ margin: 0, padding: 0, lineHeight: '1.2' }} {...props}>
                  {children}
                </ol>
              ),
              li: ({ children, ...props }) => (
                <li style={{ margin: 0, padding: 0, lineHeight: '1.2' }} {...props}>
                  {children}
                </li>
              ),
              // Custom div component to handle line breaks
              div: ({ children, ...props }) => (
                <div style={{ margin: 0, padding: 0, lineHeight: '1.2' }} {...props}>
                  {children}
                </div>
              ),
              // Custom span component
              span: ({ children, ...props }) => (
                <span style={{ margin: 0, padding: 0, lineHeight: '1.2' }} {...props}>
                  {children}
                </span>
              ),
            }}
          >
            {currentIndex < typewriterText.length ? displayedText : markdownText}
          </ReactMarkdown>
        </div>
      ) : (
        <div dangerouslySetInnerHTML={{ __html: displayedText }} />
      )}
      {currentIndex < typewriterText.length && (
        <span className="animate-pulse">|</span>
      )}
    </div>
  );
};
