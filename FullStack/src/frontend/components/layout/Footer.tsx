/**
 * Footer Component
 * Reusable footer for the application
 */

export function Footer() {
  return (
    <footer className="border-t mt-auto">
      <div className="container mx-auto px-4 py-6 text-center text-sm text-muted-foreground">
        <p>&copy; {new Date().getFullYear()} Kreeda Hiring Bot. All rights reserved.</p>
      </div>
    </footer>
  );
}
