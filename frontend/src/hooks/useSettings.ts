import { useCallback, useState } from "react";

export interface DeliverySettings {
  startTime: string; // "HH:MM" format
  dwellMinutes: number; // minutes spent at each stop
  speedKmh: number; // travel speed in km/h
}

const STORAGE_KEY = "delivery-settings";

const DEFAULTS: DeliverySettings = {
  startTime: "09:00",
  dwellMinutes: 3,
  speedKmh: 15, // bicycle default
};

function load(): DeliverySettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULTS;
    return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return DEFAULTS;
  }
}

function save(settings: DeliverySettings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

export function useSettings() {
  const [settings, setSettings] = useState<DeliverySettings>(load);

  const update = useCallback((partial: Partial<DeliverySettings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...partial };
      save(next);
      return next;
    });
  }, []);

  return { settings, update };
}
