Measured-hall IR set for the Disney Medley mix. All files are 44.1 kHz float32 stereo WAVs.
Built by scratchpad/ac_tools/build_final.py. Seat map: seating.json. Per-file metadata: manifest.json.
Measurements: ../meta/m_final.json, made with scratchpad/ac_tools/irmeasure.py.

marco_tree/   PRIMARY. St Paul's Hall, Huddersfield (converted church concert hall), from 3D-MARCo.
              13 stage azimuths, from +90 deg (far left) through 0 to -90 deg (far right), every 15 deg.
              Odd azimuths (+-90, +-60, +-30, 0) are at 3 m; the others are at 4 m.
              main_<az>deg_<d>m.wav: Decca tree. The front omnis FL/FR (DPA 4006, 2 m apart) each get the
                centre omni at -3 dB. The centre is the 2L-Cube FC: the Decca FC channel is silent in the dataset.
              amb_<az>deg_<d>m.wav: Hamasaki Square front pair (Schoeps CCM8 figure-8, nulls toward the stage).
                These files carry only the room.
              Every file shares one time origin, so the arrival-time differences between seats are real.
              Every file also shares one gain, so the level differences are real.
              RT: T30 2.3-2.4 s at 500 Hz, 2.2 s at 1 kHz, 1.9 s at 2 kHz, 1.5 s at 4 kHz, 1.0 s at 8 kHz.
              main: C80 +9..+12 dB. amb: C80 +1..+5 dB. PNR 80-98 dB. Source files are 96 kHz/24-bit.
              LICENCE: CC BY-NC 3.0 (the dataset's License.pdf and README.pdf; Zenodo metadata says cc-by-3.0).
              Non-commercial use only. Attribution: "3D-MARCo, Hyunkook Lee & Dale Johnson, Applied
              Psychoacoustics Lab, University of Huddersfield (zenodo.org/records/3477602)".

detmold_kh/   ALTERNATIVE, CC BY 4.0. Detmold Konzerthaus (about 600 seats), loudspeaker orchestra from the Detmold SRIR
              database, Set C. Sources: S1-S4 are the front row from left to right, 8 m wide. S5-S8 are the back row,
              2 m deeper and 6 m wide.
              tree_S*.wav: receiver R10 (row 1). room_S*.wav: receiver R126 (row 6, centre).
              Each is an M/S decode of a coincident omni and a lateral figure-8 (L = (M+S)/2, R = (M-S)/2).
              The direct sound is nearly centred (figure-8 null toward the stage), so pan the dry spot yourself.
              RT: T30 1.55-1.65 s at 500 Hz-1 kHz, 1.5 s at 2 kHz. C80 +4..+5.5 dB.
              The files are only 1.5 s long (dataset truncation, about -58 dB of decay). Each has a 150 ms fade.
              Attribution: Amengual Gari, Sahin, Eddy, Kob, "Open Database of Spatial Room Impulse Responses at Detmold
              University of Music", AES 149 (2020), zenodo.org/records/4116247.

generic/      Single-position halls, decoded from first-order B-format to a virtual XY cardioid pair at +-55 deg.
              jacklyons_conductor / jacklyons_stalls: Jack Lyons Concert Hall, University of York. RT 1.8 s.
                96 kHz source. Conductor position: C80 +3.8, late corr 0.78 (narrow).
                Stalls position: C80 -0.1, late corr -0.03.
              usina_m5: Usina del Arte Symphony Hall, Buenos Aires. RT 2.05 s. The source tail is zero-padded and
                the HF is band-limited to about 12.7 kHz.
              old_synthetic_hall_ir: draft 4's synthetic IR (pipeline/work/hall_ir.wav), resampled for A/B.
              OpenAIR LICENCE: CC BY 4.0. Evidence: audEERING's "openair" redistribution and other projects' records
              of the OpenAIR room pages, which are offline as of 2026-10. Attribution: "OpenAIR, AudioLab, University
              of York" plus the space name and the credited measurers.

How to use (recommended; see pipeline/notes/scout2-acoustics.md):
  for each stem:  mono = stem.mean(1) * gain
                  out += conv(mono, main[seat]) + a * conv(mono, amb[seat]) + s * delay(panned dry stem, direct_ms)
  Start with a = 0.6 and s = 0.3. Raising a makes the room larger and more distant. Raising s gives more spot detail.
  direct_ms (per instrument in seating.json) aligns the dry spot with the tree's direct arrival.
