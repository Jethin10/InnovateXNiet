import * as THREE from "three";
import { WorkTimelinePoint } from "../types";

export const WORK_TIMELINE: WorkTimelinePoint[] = [
  {
    point: new THREE.Vector3(0, 0, 0),
    year: 'Intake',
    title: 'Claims',
    subtitle: 'Skills, resume, role target',
    position: 'right',
  },
  {
    point: new THREE.Vector3(-4, -4, -3),
    year: 'Evidence',
    title: 'GitHub + Code',
    subtitle: 'Repos, coding proof, profile signals',
    position: 'left',
  },
  {
    point: new THREE.Vector3(-3, -1, -6),
    year: 'Assess',
    title: 'Backend owned',
    subtitle: 'Timed staged verification',
    position: 'left',
  },
  {
    point: new THREE.Vector3(0, -1, -10),
    year: 'Score',
    title: 'Trust model',
    subtitle: 'Readiness, risk, alignment',
    position: 'left',
  },
  {
    point: new THREE.Vector3(1, 1, -12),
    year: 'Stamp',
    title: 'Recruiter view',
    subtitle: 'Signed consent-based proof',
    position: 'right',
  }
]
