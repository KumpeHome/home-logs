import { afterRenderEffect, Component, ElementRef, input, model, viewChild } from '@angular/core';

@Component({
  selector: 'hl-initials-pad',
  template: `
    <div class="pad">
      <canvas
        #canvas
        width="240"
        height="90"
        [attr.data-test]="testId()"
        (pointerdown)="start($event)"
        (pointermove)="draw($event)"
        (pointerup)="end($event)"
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
      width: min(100%, 240px);
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
      this.restore(this.value());
    });
  }

  start(event: PointerEvent): void {
    const canvas = this.canvas()?.nativeElement;
    if (!canvas) {
      return;
    }
    this.drawing = true;
    canvas.setPointerCapture(event.pointerId);
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return;
    }
    const point = this.point(event);
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#1a1f24';
    ctx.beginPath();
    ctx.moveTo(point.x, point.y);
  }

  draw(event: PointerEvent): void {
    if (!this.drawing) {
      return;
    }
    const ctx = this.canvas()?.nativeElement.getContext('2d');
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
    const canvas = this.canvas()?.nativeElement;
    if (canvas) {
      this.value.set(canvas.toDataURL('image/png'));
    }
  }

  clear(): void {
    const canvas = this.canvas()?.nativeElement;
    const ctx = canvas?.getContext('2d');
    if (canvas && ctx) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    this.value.set('');
  }

  private restore(data: string): void {
    if (this.drawing || !data.startsWith('data:image')) {
      return;
    }
    const canvas = this.canvas()?.nativeElement;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) {
      return;
    }
    const image = new Image();
    image.onload = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    };
    image.src = data;
  }

  private point(event: PointerEvent): { x: number; y: number } {
    const canvas = this.canvas()?.nativeElement;
    if (!canvas) {
      return { x: 0, y: 0 };
    }
    const rect = canvas.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / rect.width) * canvas.width,
      y: ((event.clientY - rect.top) / rect.height) * canvas.height,
    };
  }
}
