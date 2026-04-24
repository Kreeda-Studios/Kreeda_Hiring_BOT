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
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null; // avoid hydration mismatch

  const imgSrc = resolvedTheme === "dark" ? darkImg : lightImg;

  return (
    <PageContainer className="relative min-h-[calc(100vh-4rem)] w-full max-w-none px-0">
      <div className="relative w-full h-[calc(100vh-4rem)] overflow-hidden">

        {/* 🔹 Blur layer */}
        <Image
          src={imgSrc}
          alt="blur"
          fill
          priority
          placeholder="blur"
          className={`object-cover object-bottom transition-opacity duration-700 ${
            loaded ? "opacity-0" : "opacity-100"
          }`}
        />

        {/* 🔹 Sharp layer */}
        <Image
          src={imgSrc}
          alt="Kreeda Hiring Bot"
          fill
          priority
          className={`object-cover object-bottom transition-opacity duration-700 ${
            loaded ? "opacity-100" : "opacity-0"
          }`}
          onLoadingComplete={() => setLoaded(true)}
        />
      </div>
    </PageContainer>
  );
}