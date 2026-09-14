import { afterRenderEffect, Component, ElementRef, input, model, viewChild } from '@angular/core';

const PAD_WIDTH = 240;
const PAD_HEIGHT = 90;
const MIN_DPR = 2;

@Component({
  selector: 'hl-initials-pad',
  template: `
    <div class="pad">
      <canvas
        #canvas
        [attr.data-test]="testId()"
        (pointerdown)="start($event)"
        (pointermove)="draw($event)"
        (pointerup)="end($event)"
        (lostpointercapture)="end($event)"
        (click)="$event.preventDefault(); $event.stopPropagation()"
      ></canvas>
      <button type="button" class="hl-btn secondary" (click)="clear()">Clear</button>
    </div>
  `,
  styles: `
    .pad {
      display: grid;
      gap: 0.4rem;
      justify-items: start;
    }
    canvas {
      border: 1px solid var(--hl-line);
      border-radius: 10px;
      background: #fff;
      touch-action: none;
      cursor: crosshair;
      width: min(100%, ${PAD_WIDTH}px);
      height: ${PAD_HEIGHT}px;
    }
  `,
})
export class InitialsPad {
  readonly value = model('');
  readonly testId = input('initials');
  private readonly canvas = viewChild<ElementRef<HTMLCanvasElement>>('canvas');
  private drawing = false;

  constructor() {
    afterRenderEffect(() => {
      this.prepareCanvas();
      this.restore(this.value());
    });
  }

  start(event: PointerEvent): void {
    const ctx = this.prepareCanvas();
    const canvas = this.canvas()?.nativeElement;
    if (!ctx || !canvas) {
      return;
    }
    this.drawing = true;
    canvas.setPointerCapture(event.pointerId);
    const point = this.point(event);
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#1a1f24';
    ctx.beginPath();
    ctx.moveTo(point.x, point.y);
  }

  draw(event: PointerEvent): void {
    if (!this.drawing) {
      return;
    }
    const ctx = this.context();
    if (!ctx) {
      return;
    }
    const point = this.point(event);
    ctx.lineTo(point.x, point.y);
    ctx.stroke();
  }

  end(_event: PointerEvent): void {
    if (!this.drawing) {
      return;
    }
    this.drawing = false;
    this.snapshot();
  }

  clear(): void {
    const ctx = this.prepareCanvas();
    if (ctx) {
      this.fillWhite(ctx);
    }
    this.value.set('');
  }

  snapshot(): void {
    const canvas = this.canvas()?.nativeElement;
    if (canvas) {
      this.value.set(canvas.toDataURL('image/png'));
    }
  }

  private restore(data: string): void {
    if (this.drawing || !data.startsWith('data:image')) {
      return;
    }
    const ctx = this.prepareCanvas();
    const canvas = this.canvas()?.nativeElement;
    if (!ctx || !canvas) {
      return;
    }
    const image = new Image();
    image.onload = () => {
      this.fillWhite(ctx);
      ctx.drawImage(image, 0, 0, PAD_WIDTH, PAD_HEIGHT);
    };
    image.src = data;
  }

  private prepareCanvas(): CanvasRenderingContext2D | null {
    const canvas = this.canvas()?.nativeElement;
    if (!canvas) {
      return null;
    }
    const dpr = Math.max(MIN_DPR, window.devicePixelRatio || 1);
    const width = Math.round(PAD_WIDTH * dpr);
    const height = Math.round(PAD_HEIGHT * dpr);
    const resized = canvas.width !== width || canvas.height !== height;
    if (resized) {
      canvas.width = width;
      canvas.height = height;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return null;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (resized) {
      this.fillWhite(ctx);
    }
    return ctx;
  }

  private context(): CanvasRenderingContext2D | null {
    const canvas = this.canvas()?.nativeElement;
    const ctx = canvas?.getContext('2d');
    if (!ctx || !canvas) {
      return null;
    }
    const dpr = canvas.width / PAD_WIDTH;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return ctx;
  }

  private fillWhite(ctx: CanvasRenderingContext2D): void {
    ctx.save();
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, PAD_WIDTH, PAD_HEIGHT);
    ctx.restore();
  }

  private point(event: PointerEvent): { x: number; y: number } {
    const canvas = this.canvas()?.nativeElement;
    if (!canvas) {
      return { x: 0, y: 0 };
    }
    const rect = canvas.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / rect.width) * PAD_WIDTH,
      y: ((event.clientY - rect.top) / rect.height) * PAD_HEIGHT,
    };
  }
}
