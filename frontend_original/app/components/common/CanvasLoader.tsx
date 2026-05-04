'use client';

import { useGSAP } from "@gsap/react";
import { AdaptiveDpr, Preload, ScrollControls, useProgress, useScroll } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import gsap from "gsap";
import { Suspense, useEffect, useRef, useState } from "react";
import { isMobile } from "react-device-detect";

import { usePortalStore, useThemeStore } from "@stores";

import AccountDock from "./AccountDock";
import GateLoginOverlay from "./GateLoginOverlay";
import Preloader from "./Preloader";
import ProgressLoader from "./ProgressLoader";
import { ScrollHint } from "./ScrollHint";
import ThemeSwitcher from "./ThemeSwitcher";
import ProductFeatureOverlay from "../product/ProductFeatureOverlay";
import TrustFlowSceneOverlay from "../experience/work/TrustFlowSceneOverlay";
// import {Perf} from "r3f-perf"

const CanvasLoader = (props: { children: React.ReactNode }) => {
  const ref= useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const backgroundColor = useThemeStore((state) => state.theme.color);
  const isWorkPortalActive = usePortalStore((state) => state.activePortalId === "work");
  const { progress } = useProgress();
  const [canvasStyle, setCanvasStyle] = useState<React.CSSProperties>({
    position: "absolute",
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
    opacity: 0,
    overflow: "hidden",
  });

  useEffect(() => {
    if (!isMobile) {
      const borderStyle = {
        inset: '1rem',
        width: 'calc(100% - 2rem)',
        height: 'calc(100% - 2rem)',
      };
      setCanvasStyle({ ...canvasStyle, ...borderStyle})
    }
  }, [isMobile]);

  useGSAP(() => {
    if (progress === 100) {
      gsap.to('.base-canvas', { opacity: 1, duration: 3, delay: 1 });
    }
  }, [progress]);

  useGSAP(() => {
    gsap.to(ref.current, {
      backgroundColor: backgroundColor,
      duration: 1,
    });
    gsap.to(canvasRef.current, {
      backgroundColor: backgroundColor,
      duration: 1,
      ...noiseOverlayStyle,
    });
  }, [backgroundColor]);

  const noiseOverlayStyle = {
    backgroundBlendMode: "soft-light",
    backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 600'%3E%3Cfilter id='a'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23a)'/%3E%3C/svg%3E\")",
    backgroundRepeat: "repeat",
    backgroundSize: "100px",
  };

  return (
    <div className="h-[100dvh] wrapper relative">
      <div className="h-[100dvh] relative" ref={ref}>
        <Canvas className="base-canvas"
          shadows
          style={canvasStyle}
          ref={canvasRef}
          dpr={[1, 2]}>
          {/* <Perf/> */}
          <Suspense fallback={null}>
            <ambientLight intensity={0.5} />

            <ScrollControls
              enabled={!isWorkPortalActive}
              pages={4}
              damping={0.4}
              maxSpeed={1}
              distance={1}
              style={{ zIndex: 1, pointerEvents: "auto" }}
            >
              <MainScrollLayerState isDisabled={isWorkPortalActive} />
              <AutoScrollToTrustMap />
              {props.children}
              <Preloader />
            </ScrollControls>

            <Preload all />
          </Suspense>
          <AdaptiveDpr pixelated/>
        </Canvas>
        <ProgressLoader progress={progress} />
      </div>
      <ThemeSwitcher />
      <ScrollHint />
      <AccountDock />
      <TrustFlowSceneOverlay />
      <ProductFeatureOverlay />
      <GateLoginOverlay />
    </div>
  );
};

export default CanvasLoader;

const MainScrollLayerState = ({ isDisabled }: { isDisabled: boolean }) => {
  const data = useScroll();

  useEffect(() => {
    data.el.style.zIndex = isDisabled ? "-1" : "1";
    data.el.style.pointerEvents = isDisabled ? "none" : "auto";
  }, [data.el, isDisabled]);

  return null;
};

const AutoScrollToTrustMap = () => {
  const data = useScroll();
  const { progress } = useProgress();
  const hasStartedRef = useRef(false);

  useEffect(() => {
    if (progress < 100 || hasStartedRef.current) return;
    hasStartedRef.current = true;

    const scrollElement = data.el;
    let cancelled = false;
    let userInterrupted = false;
    const markInterrupted = () => {
      userInterrupted = true;
    };
    scrollElement.addEventListener("wheel", markInterrupted, { passive: true });
    scrollElement.addEventListener("touchstart", markInterrupted, { passive: true });
    scrollElement.addEventListener("pointerdown", markInterrupted, { passive: true });

    const startTimer = window.setTimeout(() => {
      if (cancelled || userInterrupted || scrollElement.scrollTop > 40) return;
      const maxScroll = scrollElement.scrollHeight - scrollElement.clientHeight;
      const target = Math.max(0, Math.min(maxScroll * 0.99, maxScroll));
      const start = scrollElement.scrollTop;
      const distance = target - start;
      const duration = 10500;
      const startedAt = performance.now();

      const animate = (now: number) => {
        if (cancelled || userInterrupted) return;
        const elapsed = Math.min((now - startedAt) / duration, 1);
        const eased = 0.5 - Math.cos(Math.PI * elapsed) / 2;
        scrollElement.scrollTop = start + distance * eased;
        if (elapsed < 1) window.requestAnimationFrame(animate);
      };

      window.requestAnimationFrame(animate);
    }, 4500);

    return () => {
      cancelled = true;
      window.clearTimeout(startTimer);
      scrollElement.removeEventListener("wheel", markInterrupted);
      scrollElement.removeEventListener("touchstart", markInterrupted);
      scrollElement.removeEventListener("pointerdown", markInterrupted);
    };
  }, [data.el, progress]);

  return null;
};
