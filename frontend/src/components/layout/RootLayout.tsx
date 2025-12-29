import { Outlet, Link } from 'react-router-dom';
import { Server } from 'lucide-react';

export function RootLayout() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <Server className="h-6 w-6" />
            <h1 className="text-2xl font-bold">Fourdrinier</h1>
          </Link>
        </div>
      </header>
      <main className="container mx-auto px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
