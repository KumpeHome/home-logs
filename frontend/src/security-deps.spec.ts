import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function packageVersion(name: string): string {
  const lockPath = join(import.meta.dirname, '..', 'package-lock.json');
  const lock = JSON.parse(readFileSync(lockPath, 'utf8')) as {
    packages: Record<string, { version?: string } | undefined>;
  };
  return lock.packages[`node_modules/${name}`]?.version ?? '';
}

function atLeast(version: string, minimum: [number, number, number]): boolean {
  const [major, minor, patch] = version.split('.').map(Number);
  if (major !== minimum[0]) {
    return major > minimum[0];
  }
  if (minor !== minimum[1]) {
    return minor > minimum[1];
  }
  return patch >= minimum[2];
}

describe('security dependency pins', () => {
  it('overrides hono to a release that patches GHSA-crvj-82cr-hjcx and GHSA-gqvv-2mrq-wpjv', () => {
    const version = packageVersion('hono');
    const patched = version === '' || atLeast(version, [4, 13, 7]);
    expect(patched).toBe(true);
  });

  it('pins packages above the open Dependabot vulnerable ranges', () => {
    expect(atLeast(packageVersion('@angular/router'), [22, 2, 0])).toBe(true);
    expect(atLeast(packageVersion('undici'), [7, 29, 1])).toBe(true);
    expect(atLeast(packageVersion('piscina'), [5, 3, 2])).toBe(true);
    expect(atLeast(packageVersion('fast-uri'), [3, 1, 8])).toBe(true);
    const ipAddress = packageVersion('ip-address');
    expect(ipAddress === '' || atLeast(ipAddress, [10, 7, 1])).toBe(true);
  });

  it('finds frontend/package-lock.json when the process cwd is the repository root', () => {
    const previous = process.cwd();
    process.chdir(join(import.meta.dirname, '..', '..'));
    try {
      expect(packageVersion('@angular/router').length).toBeGreaterThan(0);
    } finally {
      process.chdir(previous);
    }
  });
});
