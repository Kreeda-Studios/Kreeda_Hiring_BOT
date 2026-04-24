import { PageContainer } from "@/components/common";
import Image from "next/image";

import lightImg from "@/images/KreedaHiringBot_Light.jpg";
import darkImg from "@/images/KreedaHiringBot_Dark.jpg";

export default function DashboardPage() {
  return (
    <PageContainer className="relative min-h-[calc(100vh-4rem)] w-full max-w-none px-0">
      <div className="relative w-full h-[calc(100vh-4rem)]">
        <Image
          src={lightImg}
          alt="Kreeda Hiring Bot"
          fill
          priority
          placeholder="blur"
          className="object-cover object-bottom block dark:hidden"
        />
        <Image
          src={darkImg}
          alt="Kreeda Hiring Bot"
          fill
          priority
          placeholder="blur"
          className="object-cover object-bottom hidden dark:block"
        />
      </div>
    </PageContainer>
  );
}