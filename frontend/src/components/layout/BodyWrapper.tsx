"use client";

import { useEffect, useState } from 'react';

interface BodyWrapperProps {
  children: React.ReactNode;
}

export default function BodyWrapper({ children }: BodyWrapperProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    
    // Ensure body has consistent styling
    const body = document.body;
    if (body) {
      // Remove any isolation styles that might cause hydration issues
      body.style.isolation = 'unset';
      body.style.margin = '0';
      body.style.padding = '0';
    }
  }, []);

  // During SSR and initial hydration, render without body wrapper
  if (!mounted) {
    return <>{children}</>;
  }

  // After hydration, render with body wrapper
  return (
    <div id="body-wrapper" style={{ isolation: 'unset' }}>
      {children}
    </div>
  );
}
