import axios from "axios";
import type { SessionResponse, OptimizeResponse } from "../types";

const API_BASE = "http://localhost:8000/api";

const api = axios.create({
  baseURL: API_BASE,
});

export async function uploadFile(file: File): Promise<SessionResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post<SessionResponse>("/upload/", formData);
  return data;
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  const { data } = await api.get<SessionResponse>(`/sessions/${sessionId}/`);
  return data;
}

export async function optimizeRoute(
  sessionId: string
): Promise<OptimizeResponse> {
  const { data } = await api.post<OptimizeResponse>(
    `/sessions/${sessionId}/optimize/`
  );
  return data;
}

export interface GeocodeProgress {
  stop: import("../types").DeliveryStop;
  progress: { current: number; total: number };
}

export async function geocodeStops(
  sessionId: string,
  onProgress: (data: GeocodeProgress) => void
): Promise<void> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/geocode/`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error("Geocoding request failed");
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.trim()) {
        const data: GeocodeProgress = JSON.parse(line);
        onProgress(data);
      }
    }
  }

  if (buffer.trim()) {
    const data: GeocodeProgress = JSON.parse(buffer);
    onProgress(data);
  }
}
