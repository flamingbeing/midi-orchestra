// tiny-orchestra - a tiny orchestra for the browser.
//
// A dependency-free sampler on Web Audio plus the pure helpers it is built
// from (sample choice, pitch math, beats -> time, note names, WAV), which are
// exported so they can be tested and reused without an AudioContext.
export { Orchestra } from "./orchestra.js";
export { INSTRUMENT_NAMES } from "./instruments.js";
export { midiToFreq, playbackRate, velocityGain, pickLayer, pickSample, pickVariant } from "./pitch.js";
export { beatToTime, timeToBeat, scoreLength, flattenScore, collectEvents, wrapPosition, nextBarBeat, barAt, flattenDynamics, dynamicsAt, } from "./score.js";
export { tempoMap, repeating, LiveTimeline } from "./tempo.js";
export { noteToMidi, midiToNote, toMidi, sequence } from "./notes.js";
export { encodeWav } from "./wav.js";
export { startScheduler, LOOKAHEAD, LOOKAHEAD_HIDDEN, TICK_MS } from "./scheduler.js";
export { detectOnset, decoderShift, MP3_PRIMING } from "./onset.js";
export { makeImpulse, makeupGain } from "./reverb.js";
//# sourceMappingURL=index.js.map