import type { Difficulty } from "../types/api";

export function DifficultyBadge({ difficulty }: { difficulty: Difficulty }) {
  return (
    <span className={`difficulty-badge difficulty-${difficulty}`}>
      {difficulty}
    </span>
  );
}
