export function shouldBypassOidc(envFlag: boolean, healthBypass?: boolean): boolean {
  return envFlag === true || healthBypass === true;
}
