import { useRef, useEffect, useState } from "react";

interface Player {
  x: number;
  y: number;
  size: number;
  velocityY: number;
}

interface Obstacle {
  x: number;
  gapY: number;
  gapSize: number;
  width: number;
  genre: string;
  color: string;
  passed: boolean;
}

type GameState = "idle" | "playing" | "gameOver";

// Game constants
const CANVAS_WIDTH = 500;
const CANVAS_HEIGHT = 600;
const GRAVITY = 0.5;
const FLAP_FORCE = -8;
const OBSTACLE_SPEED = 3;
const OBSTACLE_WIDTH = 70;
const GAP_SIZE = 150;
const PLAYER_SIZE = 20;
const PLAYER_X = 80;
const OBSTACLE_SPAWN_RATE = 140; // frames between obstacles

const GENRES = [
  { name: "RPG", color: "#a78bfa", glowColor: "rgba(167, 139, 250, 0.6)" },
  { name: "FPS", color: "#f87171", glowColor: "rgba(248, 113, 113, 0.6)" },
  { name: "Strategy", color: "#60a5fa", glowColor: "rgba(96, 165, 250, 0.6)" },
  { name: "Puzzle", color: "#fbbf24", glowColor: "rgba(251, 191, 36, 0.6)" },
  { name: "Adventure", color: "#34d399", glowColor: "rgba(52, 211, 153, 0.6)" },
];

export function GameFlapperGame() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [gameState, setGameState] = useState<GameState>("idle");
  const [highScore, setHighScore] = useState(0);

  const playerRef = useRef<Player>({
    x: PLAYER_X,
    y: CANVAS_HEIGHT / 2,
    size: PLAYER_SIZE,
    velocityY: 0,
  });

  const obstaclesRef = useRef<Obstacle[]>([]);
  const spawnCounterRef = useRef(0);
  const scoreRef = useRef(0);
  const keysPressed = useRef<Record<string, boolean>>({});

  // Load high score from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("gameFlappderHighScore");
    if (saved) {
      setHighScore(parseInt(saved));
    }
  }, []);

  // Generate initial obstacles
  const generateInitialObstacles = () => {
    const obstacles: Obstacle[] = [];
    for (let i = 0; i < 4; i++) {
      const randomGap = Math.random() * 240 + 60;
      const gapY = Math.max(120, Math.min(CANVAS_HEIGHT - 120, randomGap + 300));
      const genre = GENRES[Math.floor(Math.random() * GENRES.length)]!;

      obstacles.push({
        x: CANVAS_WIDTH + i * 280,
        gapY: gapY,
        gapSize: GAP_SIZE,
        width: OBSTACLE_WIDTH,
        genre: genre.name,
        color: genre.color,
        passed: false,
      });
    }
    obstaclesRef.current = obstacles;
  };

  // Initialize game on mount
  useEffect(() => {
    generateInitialObstacles();
  }, []);

  // Initialize game
  const initializeGame = () => {
    playerRef.current = {
      x: PLAYER_X,
      y: CANVAS_HEIGHT / 2,
      size: PLAYER_SIZE,
      velocityY: 0,
    };
    // Start spawn counter negative so first new obstacle appears after initial obstacles
    spawnCounterRef.current = -200;
    scoreRef.current = 0;
    // Generate fresh obstacles for new game
    generateInitialObstacles();
  };

  // Keyboard input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      keysPressed.current[e.key] = true;

      if (e.key === " " || e.key === "ArrowUp") {
        e.preventDefault();
        if (gameState === "idle") {
          setGameState("playing");
          initializeGame();
        } else if (gameState === "gameOver") {
          setGameState("idle");
          initializeGame();
        }
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      keysPressed.current[e.key] = false;
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [gameState]);

  // Game loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;

    const gameLoop = () => {
      const player = playerRef.current;
      const obstacles = obstaclesRef.current;
      const canvasCtx = ctx as CanvasRenderingContext2D;

      // Game logic
      if (gameState === "playing") {
        // Apply gravity
        player.velocityY += GRAVITY;

        // Limit velocity
        if (player.velocityY > 10) {
          player.velocityY = 10;
        }

        // Handle input
        if (keysPressed.current[" "] || keysPressed.current["ArrowUp"]) {
          player.velocityY = FLAP_FORCE;
          keysPressed.current[" "] = false;
          keysPressed.current["ArrowUp"] = false;
        }

        // Update player position
        player.y += player.velocityY;

        // Spawn obstacles
        spawnCounterRef.current++;
        if (spawnCounterRef.current > OBSTACLE_SPAWN_RATE) {
          const randomGap = Math.random() * 240 + 60;
          const gapY = Math.max(120, Math.min(CANVAS_HEIGHT - 120, randomGap + 300));
          const genre = GENRES[Math.floor(Math.random() * GENRES.length)]!;

          obstacles.push({
            x: CANVAS_WIDTH,
            gapY: gapY,
            gapSize: GAP_SIZE,
            width: OBSTACLE_WIDTH,
            genre: genre.name,
            color: genre.color,
            passed: false,
          });

          spawnCounterRef.current = 0;
        }

        // Update obstacles
        for (let i = obstacles.length - 1; i >= 0; i--) {
          const obstacle = obstacles[i]!;
          obstacle.x -= OBSTACLE_SPEED;

          // Score when passing (when obstacle passes player)
          if (!obstacle.passed && obstacle.x < player.x) {
            obstacle.passed = true;
            scoreRef.current++;
            if (scoreRef.current > highScore) {
              setHighScore(scoreRef.current);
              localStorage.setItem("gameFlappderHighScore", scoreRef.current.toString());
            }
          }

          // Remove off-screen obstacles
          if (obstacle.x + OBSTACLE_WIDTH < 0) {
            obstacles.splice(i, 1);
          }
        }

        // Collision detection
        let hasCollided = false;

        // Check boundaries
        if (player.y < 0 || player.y + player.size > CANVAS_HEIGHT) {
          hasCollided = true;
        }

        // Check obstacles
        for (const obstacle of obstacles) {
          if (
            player.x + player.size > obstacle.x &&
            player.x < obstacle.x + obstacle.width
          ) {
            // Check if NOT in gap
            if (
              player.y < obstacle.gapY - obstacle.gapSize / 2 ||
              player.y + player.size > obstacle.gapY + obstacle.gapSize / 2
            ) {
              hasCollided = true;
              break;
            }
          }
        }

        if (hasCollided) {
          setGameState("gameOver");
        }
      }

      // Rendering
      // Background
      canvasCtx.fillStyle = "rgb(15, 23, 42)";
      canvasCtx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

      // Gradient background
      const gradient = canvasCtx.createLinearGradient(0, 0, 0, CANVAS_HEIGHT);
      gradient.addColorStop(0, "rgba(5, 150, 105, 0.05)");
      gradient.addColorStop(1, "rgba(15, 23, 42, 1)");
      canvasCtx.fillStyle = gradient;
      canvasCtx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

      // Draw obstacles (always visible)
      for (const obstacle of obstaclesRef.current) {
        // Top block
        canvasCtx.fillStyle = obstacle.color;
        canvasCtx.shadowColor = obstacle.color;
        canvasCtx.shadowBlur = 15;
        canvasCtx.fillRect(
          obstacle.x,
          0,
          obstacle.width,
          obstacle.gapY - obstacle.gapSize / 2
        );

        // Bottom block
        canvasCtx.fillRect(
          obstacle.x,
          obstacle.gapY + obstacle.gapSize / 2,
          obstacle.width,
          CANVAS_HEIGHT - (obstacle.gapY + obstacle.gapSize / 2)
        );

        // Genre label
        canvasCtx.shadowBlur = 0;
        canvasCtx.fillStyle = "rgba(255, 255, 255, 0.8)";
        canvasCtx.font = "bold 11px Arial";
        canvasCtx.textAlign = "center";
        canvasCtx.fillText(
          obstacle.genre,
          obstacle.x + obstacle.width / 2,
          obstacle.gapY
        );

        canvasCtx.shadowColor = "transparent";
      }

      // Draw player
      canvasCtx.shadowColor = "#34d399";
      canvasCtx.shadowBlur = 20;
      canvasCtx.fillStyle = "#34d399";
      canvasCtx.beginPath();
      canvasCtx.arc(player.x + player.size / 2, player.y + player.size / 2, player.size / 2, 0, Math.PI * 2);
      canvasCtx.fill();

      // Player eyes
      canvasCtx.shadowBlur = 0;
      canvasCtx.fillStyle = "#1f2937";
      canvasCtx.beginPath();
      canvasCtx.arc(player.x + player.size / 2 - 5, player.y + player.size / 2 - 3, 2, 0, Math.PI * 2);
      canvasCtx.fill();
      canvasCtx.beginPath();
      canvasCtx.arc(player.x + player.size / 2 + 5, player.y + player.size / 2 - 3, 2, 0, Math.PI * 2);
      canvasCtx.fill();

      // Draw UI
      canvasCtx.fillStyle = "#f1f5f9";
      canvasCtx.font = "bold 28px Arial";
      canvasCtx.textAlign = "right";
      canvasCtx.fillText(scoreRef.current.toString(), CANVAS_WIDTH - 20, 40);

      canvasCtx.font = "12px Arial";
      canvasCtx.fillStyle = "#cbd5e1";
      canvasCtx.textAlign = "right";
      canvasCtx.fillText(`High: ${highScore}`, CANVAS_WIDTH - 20, 60);

      // Draw state overlays
      if (gameState === "idle") {
        canvasCtx.fillStyle = "rgba(0, 0, 0, 0.6)";
        canvasCtx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

        canvasCtx.fillStyle = "#f1f5f9";
        canvasCtx.font = "bold 24px Arial";
        canvasCtx.textAlign = "center";
        canvasCtx.fillText("Game Flapper", CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 - 80);

        canvasCtx.font = "14px Arial";
        canvasCtx.fillStyle = "#cbd5e1";
        canvasCtx.fillText("Avoid the game genres!", CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 - 30);

        canvasCtx.fillStyle = "#34d399";
        canvasCtx.font = "bold 16px Arial";
        canvasCtx.fillText("Press SPACE to start", CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 + 40);
      } else if (gameState === "gameOver") {
        canvasCtx.fillStyle = "rgba(0, 0, 0, 0.8)";
        canvasCtx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

        canvasCtx.fillStyle = "#ef4444";
        canvasCtx.font = "bold 28px Arial";
        canvasCtx.textAlign = "center";
        canvasCtx.fillText("Game Over!", CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 - 60);

        canvasCtx.fillStyle = "#f1f5f9";
        canvasCtx.font = "18px Arial";
        canvasCtx.fillText(`Score: ${scoreRef.current}`, CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2);

        if (scoreRef.current > highScore - 1) {
          canvasCtx.fillStyle = "#fbbf24";
          canvasCtx.font = "bold 14px Arial";
          canvasCtx.fillText("🎉 New High Score!", CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 + 40);
        }

        canvasCtx.fillStyle = "#34d399";
        canvasCtx.font = "bold 14px Arial";
        canvasCtx.fillText("Press SPACE to retry", CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 + 80);
      }

      animationFrameId = requestAnimationFrame(gameLoop);
    };

    gameLoop();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [gameState, highScore]);

  return (
    <div className="flex flex-col items-center gap-4">
      <canvas
        ref={canvasRef}
        width={CANVAS_WIDTH}
        height={CANVAS_HEIGHT}
        className="border-2 border-emerald-400 rounded-lg"
        style={{ imageRendering: "pixelated" }}
      />
      <p className="text-xs text-slate-400 text-center max-w-sm">
        {gameState === "idle"
          ? "Avoid the game genre obstacles and get the highest score!"
          : gameState === "playing"
          ? "Navigate through the gaps!"
          : "Game Over! Play again?"}
      </p>
    </div>
  );
}
