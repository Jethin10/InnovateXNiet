import { Line, Text, TextProps } from "@react-three/drei";
import { useMemo } from "react";
import * as THREE from "three";

export interface RoadmapAscentMilestone {
  title: string;
  subtitle?: string;
  year?: string;
}

interface RoadmapAscentProps {
  milestones: RoadmapAscentMilestone[];
  position?: THREE.Vector3;
  scale?: THREE.Vector3;
  showLabels?: boolean;
}

const palette = {
  fog: "#d9e7ef",
  deepFog: "#88a8b8",
  ridge: "#243440",
  ridgeMid: "#506776",
  ridgeLight: "#a8bac4",
  path: "#e9eef0",
  gold: "#e4c46a",
  ink: "#111820",
};

const reusableUp = new THREE.Vector3(0, 1, 0);

const createPathPoint = (index: number, total: number) => {
  const progress = total <= 1 ? 0 : index / (total - 1);
  const x = Math.sin(progress * Math.PI * 2.35) * 1.1 + (progress - 0.5) * 0.55;
  const y = -2.05 + progress * 4.1;
  const z = -0.3 - progress * 2.15;

  return new THREE.Vector3(x, y, z);
};

const makeMountainShape = (points: Array<[number, number]>, z = 0) =>
  new THREE.Shape(points.map(([x, y]) => new THREE.Vector2(x, y))).getPoints(8).map(
    (point) => new THREE.Vector3(point.x, point.y, z)
  );

const MilestoneNode = ({
  milestone,
  point,
  index,
  total,
  showLabels,
}: {
  milestone: RoadmapAscentMilestone;
  point: THREE.Vector3;
  index: number;
  total: number;
  showLabels: boolean;
}) => {
  const side = index % 2 === 0 ? -1 : 1;
  const isSummit = index === total - 1;
  const labelPosition = useMemo(() => new THREE.Vector3(side * 0.58, 0.08, 0.08), [side]);
  const textAlign: TextProps["textAlign"] = side < 0 ? "right" : "left";
  const anchorX: TextProps["anchorX"] = side < 0 ? "right" : "left";

  return (
    <group position={point}>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <circleGeometry args={[isSummit ? 0.2 : 0.14, 6]} />
        <meshBasicMaterial color={isSummit ? palette.gold : palette.path} transparent opacity={0.95} />
      </mesh>
      <mesh position={[0, 0, 0.05]} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[isSummit ? 0.24 : 0.18, isSummit ? 0.29 : 0.22, 6]} />
        <meshBasicMaterial color={isSummit ? palette.gold : palette.fog} transparent opacity={0.65} />
      </mesh>
      {showLabels && (
        <group position={labelPosition}>
          <Text
            font="./soria-font.ttf"
            fontSize={isSummit ? 0.18 : 0.14}
            maxWidth={1.35}
            anchorX={anchorX}
            anchorY="middle"
            textAlign={textAlign}
            color={isSummit ? palette.gold : "white"}
          >
            {milestone.title}
          </Text>
          {(milestone.year || milestone.subtitle) && (
            <Text
              font="./Vercetti-Regular.woff"
              fontSize={0.07}
              maxWidth={1.15}
              anchorX={anchorX}
              anchorY="top"
              textAlign={textAlign}
              color={palette.fog}
              position={[0, -0.16, 0]}
            >
              {[milestone.year, milestone.subtitle].filter(Boolean).join(" / ")}
            </Text>
          )}
        </group>
      )}
      {!showLabels && isSummit && (
        <group position={labelPosition}>
          <Text
            font="./soria-font.ttf"
            fontSize={0.2}
            maxWidth={1}
            anchorX={anchorX}
            anchorY="middle"
            textAlign={textAlign}
            color={palette.gold}
          >
            TRUST
          </Text>
        </group>
      )}
    </group>
  );
};

const RoadmapAscent = ({ milestones, position, scale, showLabels = true }: RoadmapAscentProps) => {
  const pathPoints = useMemo(
    () => milestones.map((_, index) => createPathPoint(index, milestones.length)),
    [milestones]
  );

  const ridgeBack = useMemo(
    () => makeMountainShape([[-2.8, -2.3], [-1.7, -0.35], [-0.65, -1.18], [0.2, -0.1], [1.15, -1.22], [2.65, -0.35], [3.05, -2.3]], -1.35),
    []
  );

  const ridgeMid = useMemo(
    () => makeMountainShape([[-3.0, -2.35], [-1.75, -1.1], [-0.6, -1.72], [0.35, -0.72], [1.45, -1.48], [2.85, -0.95], [3.15, -2.35]], -0.85),
    []
  );

  const ridgeFront = useMemo(
    () => makeMountainShape([[-2.7, -2.35], [-1.2, -1.55], [-0.2, -2.05], [0.75, -1.35], [1.65, -1.85], [2.75, -1.45], [3.05, -2.35]], -0.35),
    []
  );

  const fogBands = useMemo(
    () => [
      { position: new THREE.Vector3(-0.8, -0.9, -0.15), scale: new THREE.Vector3(2.7, 0.18, 1), opacity: 0.2 },
      { position: new THREE.Vector3(0.85, 0.25, -0.55), scale: new THREE.Vector3(2.2, 0.14, 1), opacity: 0.16 },
      { position: new THREE.Vector3(-0.25, 1.25, -0.95), scale: new THREE.Vector3(2.9, 0.16, 1), opacity: 0.13 },
    ],
    []
  );

  const candidatePosition = pathPoints[Math.max(0, Math.floor(pathPoints.length * 0.28))] ?? new THREE.Vector3();
  const summitPosition = pathPoints[pathPoints.length - 1] ?? new THREE.Vector3(0, 1.8, -2);

  return (
    <group position={position} scale={scale} rotation={[0.18, -0.08, -0.02]}>
      <group position={[0, 0, -0.7]}>
        <mesh position={[0, 0.1, -1.85]}>
          <planeGeometry args={[7, 5.6]} />
          <meshBasicMaterial color={palette.deepFog} transparent opacity={0.12} />
        </mesh>

        <Line points={ridgeBack} color={palette.ridgeLight} lineWidth={28} transparent opacity={0.28} />
        <Line points={ridgeMid} color={palette.ridgeMid} lineWidth={34} transparent opacity={0.44} />
        <Line points={ridgeFront} color={palette.ridge} lineWidth={38} transparent opacity={0.72} />

        {fogBands.map((band, index) => (
          <mesh key={index} position={band.position} scale={band.scale}>
            <planeGeometry args={[1, 1]} />
            <meshBasicMaterial color={palette.fog} transparent opacity={band.opacity} depthWrite={false} />
          </mesh>
        ))}
      </group>

      <Line points={pathPoints} color={palette.path} lineWidth={5} transparent opacity={0.78} />
      <Line points={pathPoints} color={palette.gold} lineWidth={1} transparent opacity={0.58} dashed dashSize={0.18} gapSize={0.18} />

      {pathPoints.map((point, index) => (
        <MilestoneNode
          key={`${milestones[index]?.title}-${index}`}
          milestone={milestones[index]}
          point={point}
          index={index}
          total={pathPoints.length}
          showLabels={showLabels}
        />
      ))}

      <group position={candidatePosition.clone().add(new THREE.Vector3(-0.32, -0.08, 0.12))} scale={[0.18, 0.18, 0.18]}>
        <mesh position={[0, 0.55, 0]}>
          <sphereGeometry args={[0.3, 12, 8]} />
          <meshBasicMaterial color={palette.ink} />
        </mesh>
        <mesh position={[0, -0.05, 0]}>
          <coneGeometry args={[0.42, 1.0, 4]} />
          <meshBasicMaterial color={palette.ink} />
        </mesh>
        <Line points={[new THREE.Vector3(0.08, -0.15, 0), reusableUp.clone().multiplyScalar(0.9)]} color={palette.ink} lineWidth={2} />
      </group>

      <group position={summitPosition.clone().add(new THREE.Vector3(0.1, 0.48, -0.03))}>
        <mesh rotation={[0, 0, Math.PI / 4]}>
          <boxGeometry args={[0.38, 0.38, 0.02]} />
          <meshBasicMaterial color={palette.gold} transparent opacity={0.9} />
        </mesh>
        <Text font="./Vercetti-Regular.woff" fontSize={0.12} anchorX="center" anchorY="middle" color={palette.ink} position={[0, 0, 0.03]}>
          ✓
        </Text>
      </group>
    </group>
  );
};

export default RoadmapAscent;
