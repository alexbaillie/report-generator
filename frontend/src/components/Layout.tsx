import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FileText, Home, FileStack, Layout as LayoutIcon, Edit3 } from 'lucide-react';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();

  const navItems = [
    { path: '/', icon: Home, label: 'Home' },
    { path: '/new-report', icon: FileText, label: 'New Report' },
    { path: '/editor', icon: Edit3, label: 'Text Editor' },
    { path: '/reports', icon: FileStack, label: 'Reports' },
    { path: '/templates', icon: LayoutIcon, label: 'Templates' },
  ];

  return (
    <div className="flex h-screen bg-dark-900">
      {/* Sidebar */}
      <aside className="w-64 bg-dark-800 border-r border-dark-700 flex flex-col">
        <div className="p-6 border-b border-dark-700">
          <h1 className="text-xl font-bold text-white">Psych Report Gen</h1>
          <p className="text-sm text-gray-400 mt-1">Offline AI Assistant</p>
        </div>
        
        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-primary-600 text-white'
                        : 'text-gray-300 hover:bg-dark-700'
                    }`}
                  >
                    <Icon size={20} />
                    <span>{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
