import { ReactNode } from 'react';
import Sidebar from './Sidebar';
import TitleBar from './TitleBar';
import { useAppStore } from '../stores/appStore';
import { convertFileSrc } from '@tauri-apps/api/core';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const sidebarCollapsed = useAppStore((s) => s.sidebarCollapsed);
  const backgroundImage = useAppStore((s) => s.backgroundImage);
  const backgroundOpacity = useAppStore((s) => s.backgroundOpacity);
  const backgroundBlur = useAppStore((s) => s.backgroundBlur);

  // Helper to handle background image URL
  const getBackgroundImageUrl = (path: string) => {
    if (path.startsWith('http')) return path;
    // For local files in Tauri
    return convertFileSrc(path);
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden relative bg-surface-950">
      {/* Background Image */}
      {backgroundImage && (
        <div 
          className="absolute inset-0 z-0 bg-cover bg-center bg-no-repeat transition-all duration-300"
          style={{ 
            backgroundImage: `url("${getBackgroundImageUrl(backgroundImage)}")`,
            opacity: backgroundOpacity,
            filter: `blur(${backgroundBlur}px)`,
          }}
        />
      )}

      {/* Content Overlay - gives a tint if needed, or just lets image show through */}
      {/* We rely on components having their own backgrounds (cards) or being transparent */}
      
      <div className="flex-1 flex flex-col overflow-hidden relative z-10">
        <TitleBar />
        <div className="flex-1 flex overflow-hidden">
          <Sidebar />
          <main
            className={`flex-1 overflow-auto transition-all duration-200 ${
              sidebarCollapsed ? 'ml-16' : 'ml-64'
            }`}
          >
            <div className="p-6">{children}</div>
          </main>
        </div>
      </div>
    </div>
  );
}
