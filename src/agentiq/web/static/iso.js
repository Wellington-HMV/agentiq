// Isometric projection + smooth auto-fit camera for the AGENTIQ factory.
// World coordinates are abstract floor tiles; the camera converts to screen.

export const TILE_W = 64; // screen px of one tile diagonal (x axis)
export const TILE_H = 32;

// World (tile) -> isometric screen offset, before camera pan/zoom.
export function isoX(wx, wy) {
  return ((wx - wy) * TILE_W) / 2;
}
export function isoY(wx, wy) {
  return ((wx + wy) * TILE_H) / 2;
}

export class Camera {
  constructor() {
    this.x = 0; // screen-space translation
    this.y = 0;
    this.scale = 1;
    this._target = { x: 0, y: 0, scale: 1 };
  }

  // Fit a set of world-space points (with padding) into the viewport.
  fitWorldBounds(points, viewW, viewH, padding = 90) {
    if (!points.length) return;
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const [wx, wy] of points) {
      const sx = isoX(wx, wy);
      const sy = isoY(wx, wy);
      minX = Math.min(minX, sx);
      maxX = Math.max(maxX, sx);
      minY = Math.min(minY, sy);
      maxY = Math.max(maxY, sy);
    }
    const w = maxX - minX + padding * 2;
    const h = maxY - minY + padding * 2;
    const scale = Math.min(viewW / w, viewH / h, 1.6);
    this._target = {
      scale,
      x: viewW / 2 - ((minX + maxX) / 2) * scale,
      y: viewH / 2 - ((minY + maxY) / 2) * scale,
    };
  }

  // Smoothly approach the target framing (called once per frame).
  update(dt) {
    const k = 1 - Math.exp(-dt * 3.2);
    this.x += (this._target.x - this.x) * k;
    this.y += (this._target.y - this.y) * k;
    this.scale += (this._target.scale - this.scale) * k;
  }

  // World tile -> final screen position.
  toScreen(wx, wy) {
    return [isoX(wx, wy) * this.scale + this.x, isoY(wx, wy) * this.scale + this.y];
  }
}
