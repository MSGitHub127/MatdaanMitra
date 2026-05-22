export default function ChakraWatermark() {
  return (
    <div className="fixed inset-0 pointer-events-none opacity-[0.025] z-0">
      <svg
        className="w-full h-full"
        viewBox="0 0 100 100"
        preserveAspectRatio="xMidYMid slice"
      >
        {/* First Chakra - rotates clockwise */}
        <g className="origin-center animate-spin" style={{ animationDuration: '120s' }}>
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.5"
            className="text-ink-faint"
          />
          <circle
            cx="50"
            cy="50"
            r="35"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.5"
            className="text-ink-faint"
          />
          <circle
            cx="50"
            cy="50"
            r="30"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.5"
            className="text-ink-faint"
          />
          {/* Spokes */}
          {[...Array(24)].map((_, i) => (
            <line
              key={i}
              x1="50"
              y1="10"
              x2="50"
              y2="50"
              stroke="currentColor"
              strokeWidth="0.5"
              className="text-ink-faint"
              transform={`rotate(${i * 15} 50 50)`}
            />
          ))}
        </g>

        {/* Second Chakra - rotates counter-clockwise */}
        <g className="origin-center animate-spin" style={{ animationDuration: '80s', animationDirection: 'reverse' }}>
          <circle
            cx="50"
            cy="50"
            r="25"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.5"
            className="text-ink-faint"
          />
          <circle
            cx="50"
            cy="50"
            r="20"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.5"
            className="text-ink-faint"
          />
          {/* Spokes */}
          {[...Array(12)].map((_, i) => (
            <line
              key={i}
              x1="50"
              y1="25"
              x2="50"
              y2="50"
              stroke="currentColor"
              strokeWidth="0.5"
              className="text-ink-faint"
              transform={`rotate(${i * 30} 50 50)`}
            />
          ))}
        </g>
      </svg>
    </div>
  );
}
