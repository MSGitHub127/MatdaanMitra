import { cn, getConfidenceColor } from '../../lib/utils';

interface ConfidenceRingProps {
  score: number;
  size?: number;
}

export default function ConfidenceRing({ score, size = 20 }: ConfidenceRingProps) {
  const radius = (size - 4) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score);

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="animate-spin">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        className="text-border opacity-20"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={getConfidenceColor(score)}
        strokeWidth={2}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="transition-all duration-500"
        style={{ animationDuration: '2s' }}
      />
    </svg>
  );
}
