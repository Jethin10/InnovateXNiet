'use client';

import { useProgress } from "@react-three/drei";
import gsap from "gsap";
import { useEffect, useRef } from "react";
import * as THREE from "three";
import CloudContainer from "../models/Cloud";
import HeroRiseModel from "../models/HeroRiseModel";
import StarsContainer from "../models/Stars";
import WindowModel from "../models/WindowModel";
import TextWindow from "./TextWindow";

const Hero = () => {
  const lightRef = useRef<THREE.PointLight>(null);
  const { progress } = useProgress();

  useEffect(() => {
    if (progress === 100 && lightRef.current) {
      gsap.fromTo(lightRef.current, {
        intensity: 0,
        duration: 1,
      }, {
        intensity: 34,
        duration: 2.8,
        ease: "power2.out",
      });
    }
  }, [progress]);

  return (
    <>
      <pointLight ref={lightRef} position={[0, 3.3, -6.2]} intensity={0} distance={11} color="#f4e2a2" />
      <directionalLight position={[-3.8, 4.5, -6]} intensity={1.8} color="#fff4cf" />
      <pointLight position={[3.2, 1.6, -7.4]} intensity={18} distance={7} color="#8fb8ff" />
      <HeroRiseModel />
      <StarsContainer />
      <CloudContainer/>
      <group position={[0, -25, 5.69]}>
        <pointLight castShadow position={[1, 1, -2.5]} intensity={60} distance={10}/>
        <WindowModel receiveShadow/>
        <TextWindow/>
      </group>
    </>
  );
};

export default Hero;
