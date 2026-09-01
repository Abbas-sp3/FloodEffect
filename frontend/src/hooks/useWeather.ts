import { useState, useCallback, useRef } from 'react';
import type { WeatherResult } from '../types';

export function useWeather(apiUrl: string, weatherEndpoint: string) {
  const [weatherStatus, setWeatherStatus] = useState('');
  const [weatherColor, setWeatherColor] = useState('#8b9bb4');
  const [fetching, setFetching] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchWeather = useCallback(async (): Promise<number | null> => {
    setFetching(true);
    try {
      const resp = await fetch(`${apiUrl}${weatherEndpoint}`);
      const data: WeatherResult = await resp.json();
      if (data.status === 'live') {
        setWeatherStatus(`Live: ${data.rain_mm} mm/h rainfall`);
        setWeatherColor('#4ade80');
      } else if (data.condition) {
        // KP3 format
        setWeatherStatus(`${data.condition} · ${data.rain_mm ?? 0} mm/h`);
        setWeatherColor('#4ade80');
      } else {
        setWeatherStatus('Using fallback data');
        setWeatherColor('#ff8800');
      }
      return data.intensity;
    } catch {
      setWeatherStatus('Weather fetch failed');
      setWeatherColor('#ff3366');
      return null;
    } finally {
      setFetching(false);
    }
  }, [apiUrl, weatherEndpoint]);

  const toggleAutoRefresh = useCallback(
    (onRefresh: () => void) => {
      if (autoRefresh && intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
        setAutoRefresh(false);
      } else {
        setAutoRefresh(true);
        onRefresh();
        intervalRef.current = setInterval(onRefresh, 30000);
      }
    },
    [autoRefresh]
  );

  return { weatherStatus, weatherColor, fetching, autoRefresh, fetchWeather, toggleAutoRefresh };
}
