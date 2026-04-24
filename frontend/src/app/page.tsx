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

  // Reset loading state when the theme (and thus the image src) changes
  useEffect(() => {
    setIsLoaded(false);
  }, [resolvedTheme]);

  if (!mounted) return null;

  const imgSrc = resolvedTheme === "dark" ? darkImg : lightImg;

  return (
    <PageContainer className="relative min-h-[calc(100vh-4rem)] w-full max-w-none px-0">
      <div className="relative w-full h-[calc(100vh-4rem)] overflow-hidden bg-gray-200 dark:bg-gray-800">
        
        {/* 1. The Blur Placeholder */}
        {/* We keep this visible until the main image is 100% ready */}
        <Image
          src={imgSrc}
          alt="Loading..."
          fill
          priority
          placeholder="blur"
          className={`object-cover object-bottom transition-opacity duration-1000 ${
            isLoaded ? "opacity-0" : "opacity-100"
          }`}
          style={{ filter: "blur(20px)" }} // Extra blur boost
        />

        {/* 2. The Sharp Main Image */}
        <Image
          src={imgSrc}
          alt="Kreeda Hiring Bot"
          fill
          priority
          // 'onLoad' triggers only after the image is fully downloaded and decoded
          onLoad={() => setIsLoaded(true)}
          className={`object-cover object-bottom transition-opacity duration-1000 ${
            isLoaded ? "opacity-100" : "opacity-0"
          }`}
        />
      </div>
    </PageContainer>
  );
}