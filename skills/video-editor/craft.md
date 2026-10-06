# Video editing craft

The trade behind the video-editor skill. Reason from it while you edit; cite a rule only when the owner questions a choice. The numbers here are defaults that held up on real talking-head footage, not laws: when a video disagrees with them, the video wins and the record says what worked instead.

The whole craft in one line: **a good video is not what was filmed, it is what was removed.** Editing is subtraction down to the message.

## Message-level editing

Read the whole transcript before cutting anything. You are looking for the structure of what the person meant to say, and you cannot see it from inside line 3.

• Find where the message really starts. It is almost never at second zero. "אז... רגע... בעצם מה שרציתי להגיד" is warm-up, and it goes.
• Treat a sentence as the unit. Cut on sentence boundaries from the transcript, never on arbitrary seconds.
• Remove repeated takes. When the same sentence was said twice, keep the cleaner one, which is usually the later one, because people restart when they know they stumbled.
• Remove tangents, false starts (a single word like "כי..." before the real sentence), tails that fade out, and any later sentence that only repeats the hook.
• Keep the order, unless moving one strong line to the front makes the hook. The arc that works for short video is hook, promise, proof, invitation.
• Never decide alone on a cut that removes a whole idea. Propose it with a one-line reason and let the owner decide.
• A phrase the person always says is their voice, not filler. Check their voice notes before cutting a "signature" opener or a characteristic story.

Cut tight for short video: about a tenth of a second of air between sentences reads as energy. A jump cut on a talking head is accepted on every social platform; it reads as pace, not as a mistake.

Whisper merges a doubled phrase said quickly ("שיעזור לכם, שיעזור לכם") into one in the text, so the transcript looks clean when the audio is not. When a line sounds or reads suspiciously long for its words, look at the word times: the same word twice less than a second apart is a repeat to cut.

## The hook, and the first frame

The first one to three seconds decide whether anyone watches the rest. The opening line must stop a scroll on its own: a claim, a number, a question the viewer already has, the end of the story first. "היי, היום אני רוצה לדבר על" never opens a cut.

Feeds autoplay muted, so the first frame has to work without sound: captions are on screen from the very first frame, and the face is already in frame and already talking.

## Platforms and sizes

• Vertical (Reels, TikTok, Shorts): 1080×1920, 9:16. The sweet spot for a talking head is 20 to 60 seconds; most platforms now accept longer, but every extra second has to earn itself.
• Wide (YouTube, a website, a presentation): 1920×1080, 16:9.
• Square (feed posts): 1080×1080.
• Delivery: H.264 video in 8-bit 4:2:0, AAC audio at 48 kHz, the source frame rate kept as it is (30 is the safest; never convert 30 to 60). HEVC from a phone plays badly in many browsers and editors, so deliver H.264.

Platform limits on length and file size change often. Before delivering anything long, check the platform's current limit rather than trusting a number from memory.

## Safe zones on vertical video

The app draws its own interface over the video, and anything under it is lost. On a 1080×1920 frame, keep every caption and anything that matters inside **x 110 to 930 and y 270 to 1540**. That box is the strictest of the three big apps:

• On tall phones the app fills the screen and crops about 100 px off each side.
• The right-hand action rail (like, comment, share) covers x above 930, from about y 1050 to y 1700.
• The username, the post caption and the audio line cover everything below about y 1560.
• The top bar covers everything above about y 270.

On wide video keep text inside a 5% margin on every side (96 px left and right on 1920). On square video keep about 60 px clear on every side.

## Captions in Hebrew

Most social video is watched without sound, so on vertical video captions are burned into the picture. Soft captions (a track the player can switch off) are for YouTube and websites; Instagram and TikTok ignore them.

**Chunking.** Two or three words per caption on a reel, or one big word for a fast, punchy style. At most two lines, at most about 32 characters per line. Every caption stays on screen at least about half a second: a word shorter than 0.12 s is merged with the next, so nothing flickers for one frame.

**Breaking lines.** Never separate a number from its unit ("3 שעות"), a name from its surname, or a one-letter prefix word from what follows. Do not end a line on a dangling short word.

**Direction.** Hebrew reads right to left, and English words and numbers inside it stay left to right. The renderer handles this, but it has to be checked on a real frame every time a new font or style is used: "בלי WordPress ובלי Wix", "3 שעות ביום", "(בסוגריים) 100%", "שאלה? תשובה!" must all read correctly. A question mark at the end of a Hebrew sentence appears on its left. Reversed letters, swapped words or mirrored brackets mean the font or the text shaping is wrong, and nothing is delivered until it is fixed.

**Punctuation.** Drop the full stop and the comma at the end of a caption chunk; keep question and exclamation marks.

**Spelling.** The transcript is the source of the captions, so fix misheard words before burning, especially English names written in Hebrew letters ("וורד פרס" is WordPress). Never change a word's time while fixing its spelling.

**Look.** A bold Hebrew face (weight 700 to 800), about 60 to 80 px high on a 1080-wide frame. White letters with a dark outline of 4 to 6 px, or dark letters on a solid box, so they survive any background. Contrast is physics, not taste: a caption that cannot be read on a bright wall in daylight is broken whatever the colours.

**Position.** On vertical video, around 65 to 75% of the height (y about 1250 to 1450), below the chin and inside the safe zone. Never over the face: if the face sits low in the frame, the captions move above the shoulders, not over the mouth. On wide video, centred near the bottom inside the margin.

**One caption system only.** If the source already has captions burned in, do not add a second set.

## Silence thresholds

Dead air is found by loudness: anything quieter than the threshold for longer than the minimum is a cut candidate.

• Threshold -30 dB, minimum silence 0.6 s, keep at least 0.15 s of padding around speech so no word loses its first letter, and drop any kept piece shorter than 0.2 s.
• A soft-spoken person, or a noisy room: raise the threshold to -35 to -40 dB.
• Music or a constant hum under the voice in the source: silence detection becomes unreliable. Cut from the transcript instead.
• Long-form: start gentler, removing only silences of about a second or more, and keep more padding.

When a value other than the default worked for a person, write it down. Their next video is very likely the same voice in the same room.

## Fillers, and when not to cut

Filler sounds (אה, אמ, אהה, אממ, uh, um) are cut with about 0.06 s of padding. Words like "כאילו" and "יעני" are often fillers and sometimes carry meaning, so they are cut only when the owner asks. The transcription model often leaves fillers out of the text altogether; the silence pass catches most of those.

Not every pause is dead air. Keep:

• the breath before the most important sentence, about 0.2 to 0.4 s, because it tells the viewer something is coming;
• the pause after a punchline or a question, about 0.4 to 0.8 s, because that is where the viewer gets it;
• a pause while the picture shows something (a screen, an object, a reaction);
• laughter, and the silence inside an emotional story;
• a sound that carries meaning, a surprised "אה!" is not a filler.

A cut that removes every pause makes a person sound like a machine reading.

## Music under speech

The voice is always the loudest thing. While the person talks, the music sits about 15 to 20 dB under the voice and comes back up only in the gaps; at the end it fades out over about 2 seconds. The voice itself is never turned down to make room.

**Licence first.** The music must belong to the owner or be licensed for the platform it is going to. Many free libraries are licensed per platform: a track cleared for Instagram and Facebook may not be cleared for YouTube, TikTok or a website. A trending sound inside the app is for organic posts only, never for a paid ad. An unlicensed track gets the video muted or removed after it is published. When in doubt, no music.

## Loudness

Social platforms and YouTube normalise to about -14 LUFS. Deliver -14 to -16 LUFS integrated (the louder end for short social video, the quieter end for long speech), with the true peak no higher than -1 dBTP. A video far quieter than that sounds weak next to everything around it in the feed; a video above it gets turned down and may distort on the way.

## Landscape into vertical

A centre crop of a 1920×1080 frame to 9:16 keeps only about 608 px of the width. Before choosing:

• One person, roughly centred: crop around the face, not around the centre of the frame, and check the crop on frames from the start, the middle and the end, because people move.
• Two people, a whiteboard, or a screen that matters: do not crop. Put the whole wide frame in the middle of the vertical canvas with a plain band above and below, and the captions in the lower band.
• Never stretch.

## Long-form is not a long reel

A lecture, a live or a recorded call edited for YouTube keeps its context and its breathing room: gentler silence cuts, no hunt for a hook every few seconds, soft captions or a subtitle file, loudness at the quieter end.

Reels cut out of long-form are a different job. Each one must pass three tests, judged by a stranger who sees only that reel:

1) Complete: no "as I said before", no "this" pointing at something that is not in the reel.
2) Hook: the first one or two sentences stop a scroll on their own.
3) Close: the last sentence lands on an insight, a punch or an invitation, never mid-breath.

The best reels are often stitched from two or three places in the talk. Thirty to ninety seconds, depending on the idea.

Lecture-specific traps: a quiet question from the audience sits at the noise floor and is cut as silence, so compare what was cut inside audience moments before delivering. The transcription model skips quiet voices even after they are boosted. Someone standing between the camera and the speaker ruins a reel, so check the frames of a candidate before cutting it. And transcribe recordings longer than about twelve minutes in windows of about ten, because a single long pass drifts and invents text in long silences.

## Check before the full render

Look at frames of the planned edit, with the captions in place, before spending minutes on a render:

1) The first frame is the hook line, with its caption already on screen.
2) Every caption is inside the safe zone and never on the face.
3) At most two caption lines, never a single word stranded on the second.
4) Hebrew reads right to left, and English words, numbers and brackets sit where they should.
5) Contrast holds on the brightest and the darkest frame.
6) On a crop from landscape, the face is fully inside the frame on every sampled moment.
7) Only one caption system on screen.
8) The picture is not grey and washed out. A phone video recorded in HDR looks like that when it is converted without tone mapping, and it is a technical fault, not a style.

## Failure modes, and how they look

**Success that looks like nothing happened.** The command finished cleanly, and the file is the same length as the source, or has no captions, or has no music. Every render is checked on the delivered file: its length against the edit, its streams, its loudness, and frames pulled from it. A clean exit is not proof.

**A truncated file after a crash.** The render was interrupted, and the file exists but will not open, or opens and stops early. Its length does not match the edit, and that is how it is caught. Render again; never deliver it.

**Captions drifting after the cuts.** The captions were timed to the original recording, so after every cut they run early by the length of what was removed, and the drift grows towards the end. Captions must be built from the word times mapped through the edit. Check three moments right after a cut on the delivered file: the caption on screen is the word being said.

**Transcription drift.** The model's word times can be off by one to three seconds on some passages, especially after music or a long silence. When captions are visibly early or late in one stretch only, correct those word times before burning.

**A cut into a word.** The first or last letter of a word is gone. The padding around speech was too small for this voice; raise it.

**A cloud file that is not there.** A video in OneDrive or iCloud that shows a cloud icon has not been downloaded yet. It fails as an unreadable file.

**A permission window on Mac.** The first read of a video from Downloads, Desktop or Documents can open a system window asking for access. Until the owner allows it, the read fails.

**A path with Hebrew letters or spaces.** Some tools break on it. Work on a copy with a plain English name, and report with the original name.
