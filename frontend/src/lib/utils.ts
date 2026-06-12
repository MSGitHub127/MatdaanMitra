import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export function formatDateTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Returns HH:MM in 12-hour Indian locale — used by MessageBubble timestamps. */
export function formatTime(date: Date | string): string {
  return new Date(date).toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function getConfidenceColor(score: number): string {
  if (score >= 0.85) return '#10B981'; // emerald
  if (score >= 0.70) return '#F59E0B'; // amber
  return '#F43F5E'; // rose
}

export function getConfidenceLabel(score: number): string {
  if (score >= 0.85) return 'High Confidence';
  if (score >= 0.70) return 'Medium Confidence';
  return 'Low Confidence';
}

export function generateSessionId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 15)}`;
}