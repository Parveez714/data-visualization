import React, { useMemo } from 'react';

/**
 * Deterministic PRNG to ensure the constellation looks identical on every reload
 */
function pseudoRandom(seed) {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return function () {
    return (s = (s * 16807) % 2147483647) / 2147483647;
  };
}

export default function ConstellationBackground() {
  // Generate deterministic constellation points and lines
  const { points, lines } = useMemo(() => {
    const rng = pseudoRandom(42);
    const numPoints = 48;
    const pts = [];

    for (let i = 0; i < numPoints; i++) {
      pts.push({
        id: i,
        x: Math.round(rng() * 1000) / 10, // 0 to 100%
        y: Math.round(rng() * 1000) / 10, // 0 to 100%
        radius: rng() > 0.8 ? 2.5 : rng() > 0.4 ? 1.8 : 1.2,
      });
    }

    const lns = [];
    // Connect nearby points
    for (let i = 0; i < pts.length; i++) {
      for (let j = i + 1; j < pts.length; j++) {
        const dx = pts[i].x - pts[j].x;
        const dy = pts[i].y - pts[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        // Connect if close enough
        if (dist < 18) {
          lns.push({
            id: `${i}-${j}`,
            x1: pts[i].x,
            y1: pts[i].y,
            x2: pts[j].x,
            y2: pts[j].y,
            opacity: Math.max(0.06, (1 - dist / 18) * 0.3),
          });
        }
      }
    }

    return { points: pts, lines: lns };
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      {/* Layer 0: Ambient Monochrome Background Gradient */}
      <div 
        className="absolute inset-0 bg-cover bg-center"
        style={{
          backgroundColor: '#FAFAFA',
          backgroundImage: `
            radial-gradient(circle at 15% 15%, rgba(0, 0, 0, 0.02) 0%, transparent 40%),
            radial-gradient(circle at 85% 85%, rgba(0, 0, 0, 0.03) 0%, transparent 50%),
            radial-gradient(circle at 50% 50%, rgba(0, 0, 0, 0.015) 0%, transparent 60%)
          `,
          opacity: 0.95
        }}
      />

      {/* Layer 1: Grayscale SVG Dot-and-Line Constellation Network */}
      <svg
        className="absolute inset-0 w-full h-full"
        style={{ opacity: 0.25 }}
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="none"
        viewBox="0 0 100 100"
      >
        {/* Connection Lines */}
        {lines.map((line) => (
          <line
            key={line.id}
            x1={`${line.x1}%`}
            y1={`${line.y1}%`}
            x2={`${line.x2}%`}
            y2={`${line.y2}%`}
            stroke="#000000"
            strokeWidth="0.15"
            strokeOpacity={line.opacity}
          />
        ))}

        {/* Constellation Nodes */}
        {points.map((pt) => (
          <g key={pt.id}>
            <circle
              cx={`${pt.x}%`}
              cy={`${pt.y}%`}
              r={pt.radius * 0.2}
              fill="#000000"
              fillOpacity={0.7}
            />
            <circle
              cx={`${pt.x}%`}
              cy={`${pt.y}%`}
              r={pt.radius * 0.4}
              fill="#000000"
              fillOpacity={0.08}
            />
          </g>
        ))}
      </svg>
    </div>
  );
}
