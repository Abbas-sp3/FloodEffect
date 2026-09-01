import { useState, useCallback } from 'react';
import type { FloodPoint, SimulationResult } from '../types';

export function useFloodSimulation(apiUrl: string, simulateEndpoint: string) {
  const [floodPoints, setFloodPoints] = useState<FloodPoint[]>([]);
  const [floodTimeline, setFloodTimeline] = useState<number[][]>([]);
  const [computing, setComputing] = useState(false);
  const [computeTime, setComputeTime] = useState<number | null>(null);

  const simulate = useCallback(async (intensity: number) => {
    setComputing(true);
    const startTime = performance.now();

    try {
      const response = await fetch(`${apiUrl}${simulateEndpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intensity }),
      });

      const data: SimulationResult = await response.json();
      setFloodPoints(data.points);
      setFloodTimeline(data.timeline || []);
      setComputeTime(Math.round(performance.now() - startTime));
      return data;
    } catch (e) {
      console.error('API Error:', e);
      alert('Failed to connect to API. Make sure the backend is running!');
      return null;
    } finally {
      setComputing(false);
    }
  }, [apiUrl, simulateEndpoint]);

  const clearSimulation = useCallback(() => {
    setFloodPoints([]);
    setFloodTimeline([]);
    setComputeTime(null);
  }, []);

  return { floodPoints, floodTimeline, computing, computeTime, simulate, clearSimulation };
}
