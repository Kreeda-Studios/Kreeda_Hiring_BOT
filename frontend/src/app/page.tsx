"use client";

import { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import Image from "next/image";
import { PageContainer } from "@/components/common";

import lightImg from "@/images/KreedaHiringBot_Light.jpg";
import darkImg from "@/images/KreedaHiringBot_Dark.jpg";

export default function DashboardPage() {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Force reset when theme changes so the new image doesn't "slice"
  useEffect(() => {
    setIsLoaded(false);
  }, [resolvedTheme]);

  if (!mounted) return null;

  const imgSrc = resolvedTheme === "dark" ? darkImg : lightImg;

  return (
    <PageContainer className="relative min-h-[calc(100vh-4rem)] w-full max-w-none px-0">
      {/* 1. Background Layer: 
         A solid color prevents the "white" or transparent gap while the blur is generating 
      */}
      <div className="relative w-full h-[calc(100vh-4rem)] overflow-hidden bg-[#f0f0f0] dark:bg-[#0a0a0a]">
        
        {/* 2. The Sharp Main Image (Hidden until Ready) 
           We place this FIRST in the DOM so it stays behind the blur layer 
           until we fade the blur out.
        */}
        <Image
          src={imgSrc}
          alt="Kreeda Hiring Bot"
          fill
          priority
          onLoad={() => setIsLoaded(true)}
          className="object-cover object-bottom"
          // We don't use opacity here; we just let it load behind the blur
        />

        {/* 3. The "Solid" Blur Layer 
           This sits on TOP of the sharp image. 
           It only disappears once isLoaded is true.
        */}
        <div 
          className={`absolute inset-0 z-10 transition-opacity duration-700 ease-in-out ${
            isLoaded ? "opacity-0 pointer-events-none" : "opacity-100"
          }`}
        >
          <Image
            src={imgSrc}
            alt="placeholder"
            fill
            priority
            placeholder="blur"
            className="object-cover object-bottom blur-2xl scale-110" 
            // 'scale-110' hides the white edges often caused by heavy blurring
          />
        </div>
      </div>
    </PageContainer>
  );
}