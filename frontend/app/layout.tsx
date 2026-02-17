import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { SidebarProvider } from "./components/SidebarProvider";
import LayoutContent from "./components/LayoutContent";
import { LanguageProvider } from "./contexts/LanguageContext";
import { ThemeProvider } from "./contexts/ThemeContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DB Disambiguator",
  description: "Database disambiguation and product catalog management tool",
};

// Inline script to set dark class before first paint to prevent flash
const themeScript = `
(function() {
  try {
    var theme = localStorage.getItem('app_theme');
    if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      document.documentElement.classList.add('dark');
    }
  } catch(e) {}
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ThemeProvider>
          <LanguageProvider>
            <SidebarProvider>
              <LayoutContent>{children}</LayoutContent>
            </SidebarProvider>
          </LanguageProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
