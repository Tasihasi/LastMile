export type WizardStep = 1 | 2 | 3 | 4 | 5;

/** Identity of a picked file, used to spot duplicates and unchanged selections. */
export function fileKey(f: File): string {
  return `${f.name}:${f.size}:${f.lastModified}`;
}
