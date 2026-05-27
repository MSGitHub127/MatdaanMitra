import { getConfidenceColor } from '../../lib/utils';

interface ConfidenceRingProps {
  score: number;
  size?: number;
}

/**
 * SVG confidence ring. Does NOT spin — it's a static progress arc
 * that fills based on the confidence score (0–1).
 */
export default function ConfidenceRing({ score, size = 30 }: ConfidenceRingProps) {
  const r = (size - 4) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - score);
  const color = getConfidenceColor(score);
  const cx = size / 2;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      aria-label={`AI confidence: ${Math.round(score * 100)}%`}
    >
      <title>{`AI confidence: ${Math.round(score * 100)}%`}</title>
      {/* Track */}
      <circle
        cx={cx} cy={cx} r={r}
        fill="none"
        stroke="rgba(255,255,255,0.08)"
        strokeWidth={2.2}
      />
      {/* Fill */}
      <circle
        cx={cx} cy={cx} r={r}
        fill="none"
        stroke={color}
        strokeWidth={2.2}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cx})`}
        style={{ transition: 'stroke-dashoffset 1.4s cubic-bezier(0.34, 1.56, 0.64, 1)' }}
      />
      {/* Label */}
      <text
        x={cx} y={cx + 2.5}
        textAnchor="middle"
        fontSize={size < 24 ? 6.5 : 7.5}
        fill={color}
        fontFamily="'Instrument Sans', sans-serif"
        fontWeight={700}
      >
        {Math.round(score * 100)}
      </text>
    </svg>
  );
}