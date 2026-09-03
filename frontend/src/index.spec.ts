import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const frontendRoot = join(import.meta.dirname, '..');
const indexHtml = readFileSync(join(frontendRoot, 'src/index.html'), 'utf8');

function appleTouchIconHref(): string {
  const doc = new DOMParser().parseFromString(indexHtml, 'text/html');
  const icon = doc.querySelector('link[rel="apple-touch-icon"]');
  const href = icon?.getAttribute('href');
  if (!href) {
    throw new Error('missing apple-touch-icon href');
  }
  return href;
}

describe('iOS home screen icon', () => {
  it('declares a PNG apple-touch-icon because iOS ignores WebP', () => {
    const doc = new DOMParser().parseFromString(indexHtml, 'text/html');
    const icon = doc.querySelector('link[rel="apple-touch-icon"]');
    expect(icon).toBeTruthy();
    expect(icon?.getAttribute('href')).toBe('apple-touch-icon.png');
    expect(icon?.getAttribute('sizes')).toBe('180x180');
    expect(icon?.getAttribute('href')).not.toContain('.webp');
  });

  it('ships the declared icon from the public Angular asset input', () => {
    const href = appleTouchIconHref();
    const iconPath = join(frontendRoot, 'public', href);
    expect(existsSync(iconPath)).toBe(true);

    const png = readFileSync(iconPath);
    const signature = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
    expect([...png.subarray(0, 8)]).toEqual(signature);
    const view = new DataView(png.buffer, png.byteOffset, png.byteLength);
    expect(view.getUint32(16)).toBe(180);
    expect(view.getUint32(20)).toBe(180);

    const angular = JSON.parse(
      readFileSync(join(frontendRoot, 'angular.json'), 'utf8'),
    ) as {
      projects: {
        frontend: {
          architect: {
            build: { options: { assets: { glob: string; input: string }[] } };
          };
        };
      };
    };
    const publicInput = angular.projects.frontend.architect.build.options.assets.find(
      (asset) => asset.input === 'public',
    );
    expect(publicInput?.glob).toBe('**/*');
  });
});
