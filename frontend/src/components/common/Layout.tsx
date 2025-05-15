// 레이아웃 컴포넌트
import React from 'react';
import Navigation from './Navigation';
import Header from './Header';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-cyan-900">
      {/* 헤더 */}
      <Header />
      
      {/* 메인 컨텐츠 */}
      <main className="container mx-auto px-4 py-6 max-w-7xl">
        {children}
      </main>
      
      {/* 하단 네비게이션 */}
      <Navigation />
    </div>
  );
};

export default Layout;