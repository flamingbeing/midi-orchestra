# User listening feedback (authoritative - the user CAN listen, we cannot)

On draft 1 (out/Disney_Medley_original_draft.mp3 = render_draft.py, single mix, no phrasing):
- adequately faithful
- clarinet too soft / maybe missing in some areas
- harp is nice but too loud
- flute is nice but too soft
- celesta isn't nice -> substitute a xylophone if no good celesta is found
- the main melody should be more obvious, especially when carried by clarinet or flute
- phrasing could be better
- piano is nice (tonejs piano WAV)
- cello slightly soft

Draft 2 (stages/render_draft2.py + stages/mix_draft2.py) responded with: per-stem active-RMS balance targets
(Flute 0, Clarinet 0, Violins -2, Cellos -3.5, Violas -5, Piano -4, Harp -8.5, Guitar -8, Celesta(xylophone) -10,
Glockenspiel -9, Strings Pad -9, Snare -10, Pizz -6 dB), accompaniment ducking up to 3 dB under flute/clarinet,
legato joins + phrase arches for Flute/Clarinet/Violins, messa di voce on long notes. Keep these as the starting balance
unless the user says otherwise; never regress on any point above.
- Export format: AAC in .m4a, ffmpeg -c:a aac -b:a 256k (target 220-270 kbps). (Supersedes earlier MP3/Ogg requests.)

On draft 3/3b: clarinet much more audible but needed a slight boost to match the flute (done: target +4.5); "Beauty and the Beast ..
Reflection slightly draggy" (done: +5% tempo m101-m145 + onset compensation); last harp glissando louder, guitar softer (done).
On draft 4 (lossless VSCO strings/clarinet, SSO celesta):
- clarinet sounds like air takes too long to come out - laggy attack  -> draft 5 trims the breath lead-in
- clarinet a bit distorted / over-boosted                              -> draft 5 removes the saturation, gentle +3 dB @2.2 kHz EQ only
- note loudness too inconsistent, esp. melody notes that flow together -> draft 5: per-sample levelling, phrase-smoothed velocity, one layer per phrase
- celesta not audible at all                                           -> draft 5: target -4 dB, no ducking
- 05:12-05:16 clarinet squeaking (high G5-A5 at ff)                     -> draft 5: mf layer for notes >= E5, no saturation
- user worries about the final without further input: keep producing reviewable drafts

On draft 5:
- DEALBREAKER: clarinet squeaks from 05:10 onwards and occasionally after. ROOT CAUSE (fixed in draft 6): VSCO "F#5" clarinet samples
  (really F#6 = MIDI 90) failed pitch measurement and kept nominal 78, so G5/A5 notes played an octave too high. render_v6.py now
  inherits the folder's octave offset for unmeasured samples and snaps outliers; verified: 278 clarinet notes, median 0 cents error.
  ALWAYS verify rendered pitch per note against the MIDI for every instrument in the final pipeline.
- cello slightly too soft only around 02:20 (masked by guitar in the same register) -> draft 6: +3.5 dB automation 130-152 s
- harp doesn't sound nice at 03:20, generally not very nice; Beauty and the Beast part too thumpy, maybe not enough reverb
  -> draft 6: 70 Hz HPF, -3.5 dB @180 Hz, softer attack on low strings, extra hall send
- timing at 04:10 slightly weird but acceptable-ish (investigate in final: 9/8 bar + tempo change near there, onset compensation)
- strings and flute good; piano not bad; overall improving in the right direction

EXPORT (latest user instruction, overrides FINAL_PLAN.md's Ogg note): AAC .m4a, ffmpeg -c:a aac -b:a 256k -movflags +faststart.

Draft 7 (17:55 UTC) = v7/render_v7.py + v7/lib7.py + v7/mix_v7.py on work/draft3_input.mid: measured-best techniques
(soxr, layer xfade, legato xfade, smart RR, loudness levelling, spic+trim short strings, contour expression), VCSL harp,
VSCO Snare2, VCSL glock, 3D-MARCo per-seat hall (CC BY-NC), clarinet cap/trim/EQ, cello 2:20 automation, harp EQ.

USER IS AWAY ~7 h (from 17:55 UTC). Instructions: keep improving autonomously without input until the budget ends (01:12 UTC);
primary goal: make this MIDI as close to a real orchestral recording as possible; secondary goal: make the pipeline reusable so
the user can send other MIDI files to convert. Send each meaningful new draft to the user.

On draft 7: "the balance between instruments and within each instrument between notes is MUCH MUCH worse".
Measured (v7b/noteloud.py, per-note loudness residual vs velocity, p90 adjacent-note jump): violas 3.7->8.0 dB SD, cellos 1.5->7.1,
clarinet 2.0->3.2, celesta 3.6->5.0, adjacent jumps up to 11.8 dB. Excerpt A/B showed the scout's techniques (loudness levelling,
spiccato/trim for short strings, layer xfade, smart RR) did NOT improve the full-piece consistency; the v6 engine is best.
Inter-instrument balance broke because levels were calibrated on dry stems before per-seat hall convolution.
=> Draft 7b (17:45 UTC) = v6 engine + hall mix calibrated AFTER the hall (v7b/). HARD GATE for any future change:
   v7b/noteloud.py on the full piece must not get worse than v7b for any instrument (resid SD and p90 adjacent jump), and
   per-instrument in-hall loudness must stay on the TARGET table. Never adopt a technique on excerpt evidence alone.

On draft 8: "generally good, better than the previous versions". Keep iterating toward real orchestral recordings.
Idea from the user: imitate professional musicians, e.g. how long each breath can be held (wind phrase lengths / breath points),
BUT the original MIDI must be followed (notes, pitches, tempo map; only articulation lengths / humanization <= 30 ms).
Draft 9 is NOT final. Budget for draft 9: 3 hours from this note. Export stays AAC m4a 256k.
