import { create } from 'zustand';

interface FeatureStore {
  activeFeatureKey: string | null;
  setActiveFeatureKey: (activeFeatureKey: string | null) => void;
}

export const useFeatureStore = create<FeatureStore>((set) => ({
  activeFeatureKey: null,
  setActiveFeatureKey: (activeFeatureKey) => set(() => ({ activeFeatureKey })),
}));
