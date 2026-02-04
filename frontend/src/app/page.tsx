import { PageContainer } from "@/components/common";

export default function DashboardPage() {
  return (
    <PageContainer>
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold tracking-tight text-foreground">
            Welcome to Kreeda Hiring Bot
          </h1>
          <p className="text-lg text-muted-foreground max-w-md mx-auto">
            AI-powered resume screening platform to streamline your hiring process
          </p>
        </div>
      </div>
    </PageContainer>
  );
}
