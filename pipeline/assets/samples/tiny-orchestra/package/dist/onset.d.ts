/**
 * Onset in samples - the same computation as in the sample build (which
 * imports exactly this function): 1 ms blocks, first block above -36 dB below
 * the peak, but above four times the noise floor at the start.
 * `useFloor = false` for already trimmed files: there the start is no longer
 * noise but already the tone.
 */
export declare function detectOnset(x: Float32Array, sr: number, relDb?: number, useFloor?: boolean): number;
export declare const MP3_PRIMING: readonly [number, number];
/**
 * How many seconds later the attack sits in the decoded buffer than the
 * manifest says. The manifest was measured with ffmpeg, which removes the
 * delay (as do Chrome and Firefox). If the buffer is clearly longer than
 * expected, this browser did not; then the onset measurement decides which
 * of the known priming lengths it is.
 */
export declare function decoderShift(bufferDuration: number, expectedDuration: number | undefined, foundOnset: number | null | undefined, mark: number | null | undefined): number;
//# sourceMappingURL=onset.d.ts.map