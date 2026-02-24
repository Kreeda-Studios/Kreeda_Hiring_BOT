/**
 * Header Component
 * Reusable header for the application
 */

export function Header() {
  return (
    <header className="border-b">
      <div className="container mx-auto px-4 py-4">
        <nav className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Kreeda Hiring Bot</h1>
          {/* Add navigation items here */}
        </nav>
      </div>
    </header>
  );
}
