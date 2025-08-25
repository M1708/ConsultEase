// frontend/app/layout.tsx
import "./globals.css";
import BodyWrapper from "@/components/layout/BodyWrapper";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        <BodyWrapper>
          {children}
        </BodyWrapper>
      </body>
    </html>
  );
}

/*import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "ConsultEase - AI-Powered Consulting Platform",
  description: "Streamline your consulting business with AI agents",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">{children}</div>
      </body>
    </html>
  );
}
*/
