import type { FaceDetector, FaceDetectorResult } from "@mediapipe/tasks-vision";

export interface LocalProctoringAnalysis {
  analyzed: boolean;
  faceCount: number;
  flags: string[];
  reason: string;
}

interface FaceBox {
  originX?: number;
  originY?: number;
  width?: number;
  height?: number;
}

const MEDIAPIPE_VERSION = "0.10.17";
const WASM_BASE_URL = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MEDIAPIPE_VERSION}/wasm`;
const FACE_MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite";

export function analyzeFacePresence(faceBoxes: FaceBox[], frameWidth: number, frameHeight: number): LocalProctoringAnalysis {
  const faceCount = faceBoxes.length;
  const flags: string[] = [];
  if (faceCount === 0) {
    flags.push("face_not_detected");
  }
  if (faceCount > 1) {
    flags.push("multiple_faces");
  }

  const primaryFace = faceBoxes[0];
  if (primaryFace && frameWidth > 0 && frameHeight > 0) {
    const centerX = ((primaryFace.originX ?? 0) + (primaryFace.width ?? 0) / 2) / frameWidth;
    const centerY = ((primaryFace.originY ?? 0) + (primaryFace.height ?? 0) / 2) / frameHeight;
    const widthRatio = (primaryFace.width ?? 0) / frameWidth;
    if (centerX < 0.22 || centerX > 0.78 || centerY < 0.16 || centerY > 0.84 || widthRatio < 0.1) {
      flags.push("face_off_center");
    }
  }

  return {
    analyzed: true,
    faceCount,
    flags,
    reason: flags.length
      ? `Local face proctor flagged ${flags.map((flag) => flag.replaceAll("_", " ")).join(", ")}.`
      : "Local face proctor sees one centered face.",
  };
}

export async function createLocalFaceProctor() {
  const { FaceDetector, FilesetResolver } = await import("@mediapipe/tasks-vision");
  const vision = await FilesetResolver.forVisionTasks(WASM_BASE_URL);
  const detector: FaceDetector = await FaceDetector.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: FACE_MODEL_URL,
      delegate: "GPU",
    },
    minDetectionConfidence: 0.5,
    runningMode: "VIDEO",
  });

  return {
    analyze(video: HTMLVideoElement): LocalProctoringAnalysis {
      const result: FaceDetectorResult = detector.detectForVideo(video, performance.now());
      const faceBoxes = result.detections.map((detection) => detection.boundingBox ?? {});
      return analyzeFacePresence(faceBoxes, video.videoWidth, video.videoHeight);
    },
    close() {
      detector.close();
    },
  };
}
