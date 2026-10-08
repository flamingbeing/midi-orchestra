/** Decode an audio file. Safari long knew only the callback form; cover both. */
export declare function decode(ctx: BaseAudioContext, data: ArrayBuffer): Promise<AudioBuffer>;
/** Run at most `n` tasks at once - a server on the LAN should not choke. */
export declare function limiter(n: number): <T>(task: () => Promise<T>) => Promise<T>;
/** `"a/b"` -> `"a/b/"`; empty stays empty (relative to the page). */
export declare const withSlash: (url: string) => string;
/** Folder part of a URL: `"/audio/manifest.json"` -> `"/audio/"`. */
export declare const dirOf: (url: string) => string;
//# sourceMappingURL=loader.d.ts.map