'use client';

import { useAnimations, useGLTF, useProgress, useScroll } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import { isMobile } from 'react-device-detect';
import * as THREE from 'three';
import { GLTF } from 'three-stdlib';

type RiseModelGLTF = GLTF & {
  scene: THREE.Group;
  animations: THREE.AnimationClip[];
};

const MODEL_URL = 'models/meshy-ai-rise.glb';

const HeroRiseModel = () => {
  const groupRef = useRef<THREE.Group>(null);
  const modelRef = useRef<THREE.Group>(null);
  const data = useScroll();
  const { progress } = useProgress();
  const { scene, animations } = useGLTF(MODEL_URL, true) as RiseModelGLTF;
  const model = useMemo(() => scene.clone(true), [scene]);
  const { actions } = useAnimations(animations, modelRef);

  useEffect(() => {
    model.traverse((object) => {
      if (!(object instanceof THREE.Mesh)) return;
      object.renderOrder = 30;
      object.castShadow = false;
      object.receiveShadow = false;
      object.frustumCulled = true;
      object.geometry.computeBoundingSphere();

      const materials = Array.isArray(object.material) ? object.material : [object.material];
      materials.forEach((material) => {
        if (!material) return;
        const textured = material as THREE.MeshStandardMaterial & {
          map?: THREE.Texture | null;
          normalMap?: THREE.Texture | null;
          roughnessMap?: THREE.Texture | null;
          metalnessMap?: THREE.Texture | null;
        };
        [textured.map, textured.normalMap, textured.roughnessMap, textured.metalnessMap].forEach((texture) => {
          if (!texture) return;
          texture.anisotropy = 2;
          texture.generateMipmaps = true;
          texture.needsUpdate = true;
        });
        material.depthTest = false;
        material.depthWrite = false;
        material.needsUpdate = true;
      });
    });
  }, [model]);

  useEffect(() => {
    Object.values(actions).forEach((action) => {
      if (!action) return;
      action.reset().fadeIn(0.8).play();
      action.setLoop(THREE.LoopRepeat, Infinity);
      action.timeScale = 0.55;
    });
    return () => {
      Object.values(actions).forEach((action) => action?.fadeOut(0.25));
    };
  }, [actions]);

  useFrame((state, delta) => {
    if (!groupRef.current) return;

    const t = state.clock.elapsedTime;
    const loaded = progress >= 100 ? 1 : 0;
    const scroll = data.range(0, 0.28);
    const introY = THREE.MathUtils.lerp(-6.4, isMobile ? 2.15 : 3.05, loaded);
    const targetY = introY - scroll * 2.45 + Math.sin(t * 0.72) * 0.08;
    const targetZ = -8.9 + scroll * 1.25;
    const targetScale = isMobile ? 2.95 : 5.15;

    groupRef.current.position.y = THREE.MathUtils.damp(groupRef.current.position.y, targetY, 2.4, delta);
    groupRef.current.position.z = THREE.MathUtils.damp(groupRef.current.position.z, targetZ, 2.2, delta);
    groupRef.current.rotation.x = THREE.MathUtils.damp(groupRef.current.rotation.x, -0.04 + scroll * 0.18, 2.4, delta);
    groupRef.current.rotation.y = THREE.MathUtils.damp(groupRef.current.rotation.y, Math.sin(t * 0.38) * 0.12 + scroll * 0.5, 2.2, delta);
    groupRef.current.rotation.z = THREE.MathUtils.damp(groupRef.current.rotation.z, Math.sin(t * 0.32) * 0.035, 2.5, delta);
    groupRef.current.scale.setScalar(THREE.MathUtils.damp(groupRef.current.scale.x, targetScale, 2.1, delta));
  });

  return (
    <group ref={groupRef} position={[0, -8, -10]} scale={0.001}>
      <group ref={modelRef} rotation={[0.04, -0.1, 0]}>
        <primitive object={model} />
      </group>
    </group>
  );
};

useGLTF.preload(MODEL_URL);

export default HeroRiseModel;
