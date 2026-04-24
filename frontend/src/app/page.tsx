import { PageContainer } from "@/components/common";
import Image from "next/image";

export default function DashboardPage() {
  return (
    <PageContainer className="relative min-h-[calc(100vh-4rem)] w-full max-w-none px-0">
      <div className="relative w-full h-[calc(100vh-4rem)]">
        <Image
          src="/KreedaHiringBot_Light.jpg"
          alt="Kreeda Hiring Bot"
          fill
          priority
          className="object-cover object-bottom block dark:hidden"
        />
        <Image
          src="/KreedaHiringBot_Dark.jpg"
          alt="Kreeda Hiring Bot"
          fill
          priority
          className="object-cover object-bottom hidden dark:block"
        />
      
      </div>
    </PageContainer>
  );
}
