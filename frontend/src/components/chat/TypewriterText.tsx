"use client";

import { useState, useEffect } from "react";

interface TypewriterTextProps {
  text: string;
  speed?: number; // milliseconds per character
  onComplete?: () => void;
  className?: string;
  style?: React.CSSProperties;
}

export const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  speed = 10, // Reduced from 30ms to 10ms for faster typing
  onComplete,
  className = "",
  style
}) => {
  const [displayedText, setDisplayedText] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (currentIndex < text.length) {
      const timer = setTimeout(() => {
        setDisplayedText(prev => prev + text[currentIndex]);
        setCurrentIndex(prev => prev + 1);
      }, speed);

      return () => clearTimeout(timer);
    } else if (onComplete) {
      onComplete();
    }
  }, [currentIndex, text, speed, onComplete]);

  // Reset when text changes
  useEffect(() => {
    setDisplayedText("");
    setCurrentIndex(0);
  }, [text]);

  return (
    <div className={`whitespace-pre-wrap ${className}`} style={style}>
      <div dangerouslySetInnerHTML={{ __html: displayedText }} />
      {currentIndex < text.length && (
        <span className="animate-pulse">|</span>
      )}
    </div>
  );
};
