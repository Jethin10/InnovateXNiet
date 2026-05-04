import { Text } from "@react-three/drei";
import { usePortalStore, useScrollStore } from "@stores";
import { useEffect, useMemo, useState } from "react";
import * as THREE from "three";
import { apiRequest, SkillRoadmapResponse } from "@/app/lib/api";
import TimelinePath from "./Timeline";
import { WORK_TIMELINE } from "@constants";
import { WorkTimelinePoint } from "@types";

const Work = () => {
  const isActive = usePortalStore((state) => state.activePortalId === "work");
  const { scrollProgress, setScrollProgress } = useScrollStore();
  const [generatedRoadmap, setGeneratedRoadmap] = useState<SkillRoadmapResponse | null>(null);

  useEffect(() => {
    if (!isActive) setScrollProgress(0);
  }, [isActive, setScrollProgress]);

  useEffect(() => {
    if (!isActive) return;
    let cancelled = false;
    apiRequest<SkillRoadmapResponse>("/api/v1/pipeline/roadmap")
      .then((roadmap) => {
        if (!cancelled) setGeneratedRoadmap(roadmap);
      })
      .catch(() => {
        if (!cancelled) setGeneratedRoadmap(null);
      });
    return () => {
      cancelled = true;
    };
  }, [isActive]);

  const timeline = useMemo(
    () => buildRoadmapTimeline(generatedRoadmap),
    [generatedRoadmap]
  );

  return (
    <group>
      <mesh receiveShadow>
        <planeGeometry args={[4, 4, 1]} />
        <shadowMaterial opacity={0.1} />
      </mesh>
      <mesh position={[0, 0, 0.18]}>
        <planeGeometry args={[4.02, 4.02, 1]} />
        <meshBasicMaterial color="#c8a875" />
      </mesh>
      <mesh position={[0, -2.4, -5]}>
        <planeGeometry args={[18, 18, 1]} />
        <meshBasicMaterial color="#c8a875" />
      </mesh>
      <group position={[-0.95, 0.15, 0.32]}>
        <mesh position={[0, 0, -0.04]}>
          <planeGeometry args={[1.58, 1.82, 1]} />
          <meshBasicMaterial color="#050508" />
        </mesh>
        <Text
          font="./soria-font.ttf"
          color="white"
          fontSize={0.22}
          anchorX="center"
          anchorY="middle"
          maxWidth={1.1}
          textAlign="center"
          position={[0, 0.28, 0]}
        >
          TRUST{"\n"}FLOW{"\n"}MAP
        </Text>
        <Text
          font="./Vercetti-Regular.woff"
          color="#a7f3d0"
          fontSize={0.045}
          anchorX="center"
          anchorY="middle"
          maxWidth={1.15}
          textAlign="center"
          position={[0, -0.62, 0]}
        >
          GENERATED ROADMAP PIPELINE
        </Text>
      </group>
      <group position={[0.92, 0.18, 0.3]}>
        {[0, 1, 2].map((index) => (
          <mesh key={index} position={[0, -index * 0.36, -0.02]}>
            <planeGeometry args={[1.25, 0.25, 1]} />
            <meshBasicMaterial color={index === 0 ? "#123329" : "#111116"} />
          </mesh>
        ))}
        <Text
          font="./Vercetti-Regular.woff"
          color="white"
          fontSize={0.07}
          anchorX="left"
          anchorY="middle"
          maxWidth={1.05}
          position={[-0.55, 0, 0.02]}
        >
          Backend SDE Roadmap
        </Text>
        <Text
          font="./Vercetti-Regular.woff"
          color="#cbd5e1"
          fontSize={0.045}
          anchorX="left"
          anchorY="middle"
          maxWidth={1.02}
          position={[-0.55, -0.36, 0.02]}
        >
          Stage 1 / Algorithms
        </Text>
        <Text
          font="./Vercetti-Regular.woff"
          color="#cbd5e1"
          fontSize={0.045}
          anchorX="left"
          anchorY="middle"
          maxWidth={1.02}
          position={[-0.55, -0.72, 0.02]}
        >
          Harness tasks + proof
        </Text>
      </group>
      <TimelinePath progress={isActive ? scrollProgress : 0} timeline={timeline} />
    </group>
  );
};

const roadmapPoints = [
  new THREE.Vector3(0, 0, 0),
  new THREE.Vector3(-3.6, -3.2, -2.4),
  new THREE.Vector3(-2.6, -1.3, -5.2),
  new THREE.Vector3(0.1, -1.2, -8.0),
  new THREE.Vector3(1.2, 0.8, -10.6),
  new THREE.Vector3(1.6, 1.2, -12.5),
];

function buildRoadmapTimeline(roadmap: SkillRoadmapResponse | null): WorkTimelinePoint[] {
  if (!roadmap || roadmap.roadmap.length === 0) return WORK_TIMELINE;
  const generated = roadmap.roadmap.slice(0, 5).map((item, index) => ({
    point: roadmapPoints[index + 1] ?? new THREE.Vector3(index, -index, -index * 2),
    year: item.priority,
    title: item.skill,
    subtitle: `${item.duration} / +${item.job_impact.estimated_match_lift_percent}% match / ${Math.round(item.progress_percent)}% done`,
    position: index % 2 === 0 ? "left" : "right",
  } satisfies WorkTimelinePoint));

  return [
    {
      point: roadmapPoints[0],
      year: "Intake",
      title: "Claims",
      subtitle: `${roadmap.skill_gaps.length} gaps saved from resume analysis`,
      position: "right",
    },
    ...generated,
  ];
}

export default Work;
