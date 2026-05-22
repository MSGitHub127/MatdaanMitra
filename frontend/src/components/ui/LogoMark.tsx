export default function LogoMark({ size = 24 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Ashoka Chakra simplified */}
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="1.5"
        className="text-saffron"
      />
      <circle
        cx="12"
        cy="12"
        r="7"
        stroke="currentColor"
        strokeWidth="1"
        className="text-saffron"
      />
      <circle
        cx="12"
        cy="12"
        r="4"
        stroke="currentColor"
        strokeWidth="0.5"
        className="text-saffron"
      />
      {/* Spokes */}
      {[...Array(24)].map((_, i) => (
        <line
          key={i}
          x1="12"
          y1="2"
          x2="12"
          y2="12"
          stroke="currentColor"
          strokeWidth="0.5"
          className="text-saffron"
          transform={`rotate(${i * 15} 12 12)`}
        />
      ))}
    </svg>
  );
}
