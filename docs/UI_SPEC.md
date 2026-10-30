# Recreate the static app + Worker: Last Sentence

Input: (a) reverse-engineered from ~/dev/last-sentence/web @ 9965c12dee396fbf763a21504428a8b859b6fbc0
Design system: code-tokens — web/style.css; native HTML controls and the existing CSS component classes.
Recon: task-comparable — exit-alert apps and Story-Driven (UIST 2024) per docs/PRIOR_ART.md; this run uses the saved prior-art document, and does not claim a newly inspected competitor UI or a comparative design verdict.
Deployment form: existing static assets produced by scripts/build.mjs, served with the Cloudflare Worker API. Preserve the current web/index.html, web/style.css and ES module web/app.js structure. This document records the existing composition and constants; it does not authorize deployment, billable requests or account changes.
Hardcode the source-derived values below and preserve the complete CSS source in Fixed parameters. Exact source line numbers refer to this pinned web snapshot.

## What it is

A subway story prototype with a **sentence-and-journey replay** as its dominant interaction. Readers choose a recorded or synthetic route window, play an authored story, and inspect the Conductor log and explicit measurement provenance. A connected model path is optional and visibly separate from authored text. Known replay clocks, real browser speech-end events and prospective train ETA are separate evidence types. Station observations do not establish door-opening timing. No decorative signature effect is required by this source.

The page scrolls in normal document flow. Main content has no fixed-position overlays. A native modal dialog opens only from Connection settings.

Sections in DOM order: masthead → intro → journey controls → source controls → status notice → Live panel (hidden in Replay) → workspace (story, Conductor, journey timeline, Receipts) → provenance → footer → connection dialog.

## Page shell & libraries

Use HTML lang=en initially, UTF-8, viewport width=device-width,initial-scale=1, theme-color #f7f5ee and title Last Sentence. Link ./style.css; load ./app.js as type=module. Sources: web/index.html:2-10. There is no application framework, CDN, remote font request, external icon library or asset-loading preloader. Fonts use the exact system stacks in Fixed parameters. SVGs are inline.

Global rules, component selectors and responsive overrides are copied verbatim in Fixed parameters. The build copies source and documentation through scripts/build.mjs; same-origin API endpoints are resolved by the Worker. Service connection overrides select a configured Worker URL; session access token stays only in tab memory (web/index.html:51; web/app.js:195-202).

## Layout & sections (in order)

- Header/layout: shell max-width 1512px; shell padding 0 64px; masthead height 112px; workspace columns minmax(0,2.2fr) minmax(270px,1fr); gap 18px; cards border 1px solid var(--line), radius 7px. Story minimum height 360px; story padding 26px 30px 23px; story typography margin 35px 25px 32px. All values: web/style.css:1.
- Typography: body Arial,Helvetica,sans-serif; serif Georgia,'Times New Roman',serif. Heading font 400 clamp(36px,3.25vw,49px)/1.08 var(--serif), letter-spacing -1.8px. Story font 400 clamp(26px,2.8vw,40px)/1.27 var(--serif), letter-spacing -.8px, maximum width 690px, minimum height 104px. Korean story Georgia,'Apple SD Gothic Neo','Malgun Gothic',serif, font-size clamp(26px,2.5vw,36px), letter-spacing -.7px, line-height 1.45. Sources: web/style.css:1.
- Responsive thresholds, inclusive as authored: min-width:1450px; max-width:1100px; max-width:780px; max-width:540px. At max-width:540px the shell padding is 0 18px, heading font-size 36px, workspace is minmax(0,1fr) with gap 13px, story minimum height 329px, story padding 20px, story font-size 31px, Korean story font-size 28px; all overrides preserve their original cascade. Sources: web/style.css:2-5,9-10,13-14,17.
- Reading indicator pulse: animation:pulse 1.6s infinite; @keyframes pulse{50%{opacity:.25}}. Train marker transition:left .15s linear; marker transform:translateX(-50%). Sources: web/style.css:1.
- Reduced motion: @media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;animation:none!important;transition:none!important}}. Source: web/style.css:6. CSS motion stops; replay time still advances when started. Touch uses the same native buttons, selects and range input; there is no hover-only action or touch-specific animation path. Dialog and native form controls receive their own clicks; no separate painted interaction surface exists.
- Story scheduling: cps=4.51; margin=20; finish=Math.max(.2,duration-3); each natural sentence duration Math.max(2,[...text].length/4.51); scale=Math.min(1,finish*.84/sum). Scheduling is a virtual character-rate model when sound is off. Source: web/app.js:7-15.
- Playback defaults: mode='replay', language='en', speed=4, sound=false; source switches to recorded when its validated manifest has journeys. Speed buttons are 1×, 4×, 16×; audio sets speed to 1. Sources: web/app.js:4,186-189,385,523-530 and web/index.html:41.
- Clock: requestAnimationFrame tick clamps the per-frame delta to 2 seconds; elapsed increments delta*speed. Audio timeout is duration()+180 seconds. Live polls after 20000 ms when visible. HTTP timeout defaults: /api/plan 90000 ms, /api/write 45000 ms, other paths 25000 ms. Sources: web/app.js:140-151,195,290.
- Logs retain 20 entries; receipts retain 50 entries. Tokens show reported total_tokens or prompt_tokens+completion_tokens; absent tokens, costs and latency remain unreported. Display precision: cost toFixed(6), rounded latency ms. Source: web/app.js:54-61,207-211.
- Line colour mapping: {'2호선':'#727d58','5호선':'#8b7897','7호선':'#8c8951'}. Source: web/app.js:3.
- Measured viewport/composition/hook metrics are outside this source-derived contract; no minimum fill ratio, full-frame animation event, total visible-element limit or universal font count is specified by the existing app.

### Masthead and intro

Keep the linked L· mark, product name, Korean subline, prototype marker and Connection settings button. The intro is flex with a route-story headline and adjacent explanation; responsive overrides make the intro block at the authored mobile threshold. Sources: web/index.html:14-20 and web/style.css:1-5.

### Journey and source controls

Replay/Live and EN/한국어 are button groups with aria-pressed states; line, exit, source, journey and boarding are native selects with associated labels. Boot prefers valid recorded observations and otherwise uses the synthetic manifest. Source provenance is visible beneath the controls. Sources: web/index.html:22-30; web/app.js:523-532.

### Workspace

Story and Conductor form the initial grid row. Journey timeline and Receipts follow in DOM order. The mobile layout makes story, timeline, Conductor, Receipts separate rows in that order. Preserve the authored CSS cascade rather than reordering DOM to match one viewport. Sources: web/index.html:32-44; web/style.css:1-5,8-9,13-14,17.

The story panel shows chapter, sound control, story title, sentence counter, current sentence, progress rules and authorship status. The Conductor panel shows local planning or actual connected status, time left, story character budget, timestamped operations and model status. The timeline shows route/station names, exit designation, train marker, range scrubber, elapsed/duration clocks, playback controls and eventual schedule/speech result. Receipts starts empty; actual service events retain reported model, tokens, cost and latency, including unknown outcomes. Never insert example receipts to make this panel appear populated. Sources: web/index.html:33-43; web/app.js:94-165,207-211.

### Provenance, footer and connection dialog

Keep the limitations link and visible source distinction. Tab hiding stops connected requests/Live monitoring and pauses replay; explicit action is required to resume. The connection modal is the native dialog, not an overlay containing a second set of controls. Sources: web/index.html:46-51; web/app.js:390,404-406.

### Static copy registry (verbatim)

The following registry is extracted from the pinned web/index.html text nodes in DOM order; it includes the HTML fallback strings that may be replaced after boot. Retain the dynamic source-aware strings below as well.

- Copy verbatim: 'Last Sentence'
- Copy verbatim: 'L'
- Copy verbatim: '·'
- Copy verbatim: '마지막 문장'
- Copy verbatim: 'WORKING PROTOTYPE'
- Copy verbatim: 'A SMALL STORY FOR THE WAY HOME'
- Copy verbatim: 'Every journey deserves'
- Copy verbatim: 'a good ending'
- Copy verbatim: '.'
- Copy verbatim: 'A story that follows your train.'
- Copy verbatim: 'The last sentence is your cue to step out.'
- Copy verbatim: 'Replay'
- Copy verbatim: 'DEMO'
- Copy verbatim: 'Live'
- Copy verbatim: 'SEOUL METRO'
- Copy verbatim: 'Line 2 · 2호선'
- Copy verbatim: 'Line 5 · 5호선'
- Copy verbatim: 'Line 7 · 7호선'
- Copy verbatim: '→'
- Copy verbatim: 'YOUR EXIT'
- Copy verbatim: 'EN'
- Copy verbatim: '한국어'
- Copy verbatim: 'SOURCE'
- Copy verbatim: 'Authored timing fixture'
- Copy verbatim: 'Recorded train observations (unavailable)'
- Copy verbatim: 'JOURNEY'
- Copy verbatim: 'BOARDING AT'
- Copy verbatim: 'Synthetic timing · authored story · no model calls'
- Copy verbatim: 'EXPERIMENTAL LIVE CONNECTION'
- Copy verbatim: 'Connect a train, then a story.'
- Copy verbatim: 'Checking the configured service…'
- Copy verbatim: 'An actual station-arrival observation is required before a forecast.'
- Copy verbatim: 'Your actual train and direction'
- Copy verbatim: 'No live positions loaded'
- Copy verbatim: 'Your exit'
- Copy verbatim: 'Choose an anchored train first'
- Copy verbatim: 'Refresh positions'
- Copy verbatim: 'Start live story'
- Copy verbatim: 'Stop story'
- Copy verbatim: 'Live starts only after a fresh, verified arrival anchor and a validated route ETA. A connected story uses billable model calls. Wall-clock time continues during generation; station observations are not door sensors. Real live inference and arrival accuracy remain unmeasured.'
- Copy verbatim: 'PROLOGUE / A NOTE LEFT BEHIND'
- Copy verbatim: 'Sound off'
- Copy verbatim: 'THE YELLOW ENVELOPE'
- Copy verbatim: '01 / 12'
- Copy verbatim: 'Someone had left a yellow envelope on the seat beside you.'
- Copy verbatim: 'Hand-authored story · synthetic journey'
- Copy verbatim: 'READY WHEN YOU ARE'
- Copy verbatim: 'BEHIND THE STORY'
- Copy verbatim: 'The Conductor'
- Copy verbatim: 'LOCAL PROPOSALS'
- Copy verbatim: 'A local rule proposes scene changes as the known replay clock advances. The authored story stays fixed.'
- Copy verbatim: 'REPLAY TIME LEFT'
- Copy verbatim: '09:20'
- Copy verbatim: 'STORY BUDGET'
- Copy verbatim: '2,435'
- Copy verbatim: 'chars'
- Copy verbatim: 'Designed for Nemotron 3.5 Lightning'
- Copy verbatim: 'Not connected · no model calls in replay'
- Copy verbatim: 'YOUR JOURNEY'
- Copy verbatim: '2'
- Copy verbatim: '강남'
- Copy verbatim: '종합운동장'
- Copy verbatim: 'ONE DIRECTION'
- Copy verbatim: 'FIXTURE ARRIVAL'
- Copy verbatim: 'THE ENVELOPE'
- Copy verbatim: 'A CHANGE OF PLAN'
- Copy verbatim: 'THE LAST SENTENCE'
- Copy verbatim: '↗'
- Copy verbatim: '00:00'
- Copy verbatim: 'Start story'
- Copy verbatim: 'SPEED'
- Copy verbatim: '1×'
- Copy verbatim: '4×'
- Copy verbatim: '16×'
- Copy verbatim: 'Virtual speech clock · text only'
- Copy verbatim: 'FIXTURE SCHEDULE ERROR'
- Copy verbatim: '−3 s'
- Copy verbatim: 'Compared with the synthetic station-arrival event. This is a scheduler check, not measured train or speech performance.'
- Copy verbatim: 'Receipts'
- Copy verbatim: '0 API CALLS'
- Copy verbatim: 'No inference receipts yet.'
- Copy verbatim: 'The replay uses authored text and local rules. Model tokens, cost and latency appear only after real API responses.'
- Copy verbatim: 'Generate with connected models'
- Copy verbatim: 'Return to authored story'
- Copy verbatim: 'Optional billable requests · inference reservation cap ≤ $3; Tavily separate. Account billing may differ.'
- Copy verbatim: 'Read the measurement status'
- Copy verbatim: 'i'
- Copy verbatim: 'An honest replay.'
- Copy verbatim: 'The three routes and stories are authored fixtures. Arrival means a simulated station event; door opening and real-world accuracy have not been measured.'
- Copy verbatim: 'Read the limitations ↗'
- Copy verbatim: 'NO ACCOUNT NEEDED'
- Copy verbatim: 'LAST SENTENCE'
- Copy verbatim: 'SEOUL, 2026'
- Copy verbatim: 'Conductor + Writer'
- Copy verbatim: '/'
- Copy verbatim: 'Built for a better ending.'
- Copy verbatim: 'Service connection'
- Copy verbatim: '×'
- Copy verbatim: 'Replay works without a service. A configured Worker can provide live positions and model receipts.'
- Copy verbatim: 'Worker URL'
- Copy verbatim: 'Session access token'
- Copy verbatim: 'The token stays in this tab’s memory. It is never saved to storage or sent outside the chosen service.'
- Copy verbatim: 'Clear'
- Copy verbatim: 'Save connection'

### Dynamic labels and limitation notices (verbatim)

- Playback labels copy verbatim: 'Start story | Pause | Continue | Play again | Restart story | Sound on | Sound off'
- Available recorded source copy verbatim: 'Recorded train observations'
- Recorded arrival label copy verbatim: 'RECORDED DURATION'
- Scheduler result label copy verbatim: 'REPLAY SCHEDULE ERROR'
- Audio unavailable label copy verbatim: 'AUDIO LANDING ERROR'
- Audio pending label copy verbatim: 'SPEECH END NOT YET OBSERVED'
- Observed speech label copy verbatim: 'SPEECH VS OBSERVATION'
- Fixture speech label copy verbatim: 'BROWSER SPEECH VS FIXTURE'
- No speech engine copy verbatim: 'No browser speech engine is available. Text-only replay uses a virtual clock.'
- Korean authorship notice copy verbatim: '한국어 대본은 사람이 쓴 예시입니다. 실제 한국어 모델 실행은 아직 측정하지 않았습니다.'
- English authorship notice copy verbatim: 'English text is an authored fixture. No Writer model was run.'
- Empty keyless receipt copy verbatim: 'No inference receipts yet.'
- Recorded provenance copy verbatim: 'Recorded observations. '
- Recorded timing limitation copy verbatim: 'The story is authored unless connected models are explicitly used. Provider lag and door-opening offsets are unmeasured. '

Dynamic text templates preserve their qualifiers, numeric units and variable substitutions exactly as implemented in web/app.js:94-165,207-211,254,290,302-305,404-406,480-520. In particular, an unavailable speech result must never be replaced with the virtual schedule error. The keyless recorded scheduler's final figure is computed against a known observation timeline, and is not prospective ETA, door timing or model-backed narration performance.

## Sentence-and-journey replay — mechanics

- Header/layout: shell max-width 1512px; shell padding 0 64px; masthead height 112px; workspace columns minmax(0,2.2fr) minmax(270px,1fr); gap 18px; cards border 1px solid var(--line), radius 7px. Story minimum height 360px; story padding 26px 30px 23px; story typography margin 35px 25px 32px. All values: web/style.css:1.
- Typography: body Arial,Helvetica,sans-serif; serif Georgia,'Times New Roman',serif. Heading font 400 clamp(36px,3.25vw,49px)/1.08 var(--serif), letter-spacing -1.8px. Story font 400 clamp(26px,2.8vw,40px)/1.27 var(--serif), letter-spacing -.8px, maximum width 690px, minimum height 104px. Korean story Georgia,'Apple SD Gothic Neo','Malgun Gothic',serif, font-size clamp(26px,2.5vw,36px), letter-spacing -.7px, line-height 1.45. Sources: web/style.css:1.
- Responsive thresholds, inclusive as authored: min-width:1450px; max-width:1100px; max-width:780px; max-width:540px. At max-width:540px the shell padding is 0 18px, heading font-size 36px, workspace is minmax(0,1fr) with gap 13px, story minimum height 329px, story padding 20px, story font-size 31px, Korean story font-size 28px; all overrides preserve their original cascade. Sources: web/style.css:2-5,9-10,13-14,17.
- Reading indicator pulse: animation:pulse 1.6s infinite; @keyframes pulse{50%{opacity:.25}}. Train marker transition:left .15s linear; marker transform:translateX(-50%). Sources: web/style.css:1.
- Reduced motion: @media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;animation:none!important;transition:none!important}}. Source: web/style.css:6. CSS motion stops; replay time still advances when started. Touch uses the same native buttons, selects and range input; there is no hover-only action or touch-specific animation path. Dialog and native form controls receive their own clicks; no separate painted interaction surface exists.
- Story scheduling: cps=4.51; margin=20; finish=Math.max(.2,duration-3); each natural sentence duration Math.max(2,[...text].length/4.51); scale=Math.min(1,finish*.84/sum). Scheduling is a virtual character-rate model when sound is off. Source: web/app.js:7-15.
- Playback defaults: mode='replay', language='en', speed=4, sound=false; source switches to recorded when its validated manifest has journeys. Speed buttons are 1×, 4×, 16×; audio sets speed to 1. Sources: web/app.js:4,186-189,385,523-530 and web/index.html:41.
- Clock: requestAnimationFrame tick clamps the per-frame delta to 2 seconds; elapsed increments delta*speed. Audio timeout is duration()+180 seconds. Live polls after 20000 ms when visible. HTTP timeout defaults: /api/plan 90000 ms, /api/write 45000 ms, other paths 25000 ms. Sources: web/app.js:140-151,195,290.
- Logs retain 20 entries; receipts retain 50 entries. Tokens show reported total_tokens or prompt_tokens+completion_tokens; absent tokens, costs and latency remain unreported. Display precision: cost toFixed(6), rounded latency ms. Source: web/app.js:54-61,207-211.
- Line colour mapping: {'2호선':'#727d58','5호선':'#8b7897','7호선':'#8c8951'}. Source: web/app.js:3.
- Measured viewport/composition/hook metrics are outside this source-derived contract; no minimum fill ratio, full-frame animation event, total visible-element limit or universal font count is specified by the existing app.

The train marker and rail progress use the same railFraction=(leg+legFraction)/(state.stations.length-1); legFraction interpolates between the surrounding station timestamps. Both left and width use railFraction*100%. The station dots are equally spaced in the same rail region. The marker is display-only (aria-hidden); the native range input receives scrub interactions. Sources: web/app.js:110-121; web/index.html:41.

Keyboard and touch use native buttons, selects and range inputs. CSS :focus-visible uses outline:3px solid #8f791f and outline-offset:4px (web/style.css:1). No interactive target is painted on a separate bitmap; standard DOM layout controls hit testing.

Speech support is detected with 'speechSynthesis' in window and 'SpeechSynthesisUtterance' in window; a matching language voice is also required (web/app.js:167-189). Fallback path: authored text and the explicitly named virtual speech clock remain available, while audio timing is unmeasured. Turning sound on sets normal speed; pausing, scrubbing, switching language, acceleration or interrupted speech invalidates continuous audio measurement. Only a continuous actual browser onend for the last sentence produces a speech-end timestamp. Request cancellation retains actual or unknown service cost evidence.

Worker-backed Conductor/Writer behavior, receipt-v2 requested/provider identity checks and reservations are behavior contracts. The frontend's received-event rendering does not by itself validate a receipt-v2 identity. At this snapshot, keyless replay uses local rules and authored sentences; the models' actual behavior remains unmeasured until authenticated receipts are available. Model status and limitation copy are fixed semantics, not editable marketing labels.

## The loader / reveal

There is no separate loader. Static HTML and system fonts render at rest before the ES module finishes fetching replay manifests. The initial authored sentence is already in HTML. On valid data, boot replaces journey controls and selects a recorded source when available. If fixture loading fails, the status notice explains serving over HTTP, and Replay/line/exit controls are disabled. There is no reveal opacity animation or delayed content entrance. Reduced-motion removes the running indicator pulse and train transition; touch keeps the same immediate content. Sources: web/index.html:20-43; web/app.js:523-532; web/style.css:6.

## Fixed parameters (bake these in)

This section re-declares every source-derived constant and every required copy string from the body. No values in this snapshot are proposed design changes.

- Header/layout: shell max-width 1512px; shell padding 0 64px; masthead height 112px; workspace columns minmax(0,2.2fr) minmax(270px,1fr); gap 18px; cards border 1px solid var(--line), radius 7px. Story minimum height 360px; story padding 26px 30px 23px; story typography margin 35px 25px 32px. All values: web/style.css:1.
- Typography: body Arial,Helvetica,sans-serif; serif Georgia,'Times New Roman',serif. Heading font 400 clamp(36px,3.25vw,49px)/1.08 var(--serif), letter-spacing -1.8px. Story font 400 clamp(26px,2.8vw,40px)/1.27 var(--serif), letter-spacing -.8px, maximum width 690px, minimum height 104px. Korean story Georgia,'Apple SD Gothic Neo','Malgun Gothic',serif, font-size clamp(26px,2.5vw,36px), letter-spacing -.7px, line-height 1.45. Sources: web/style.css:1.
- Responsive thresholds, inclusive as authored: min-width:1450px; max-width:1100px; max-width:780px; max-width:540px. At max-width:540px the shell padding is 0 18px, heading font-size 36px, workspace is minmax(0,1fr) with gap 13px, story minimum height 329px, story padding 20px, story font-size 31px, Korean story font-size 28px; all overrides preserve their original cascade. Sources: web/style.css:2-5,9-10,13-14,17.
- Reading indicator pulse: animation:pulse 1.6s infinite; @keyframes pulse{50%{opacity:.25}}. Train marker transition:left .15s linear; marker transform:translateX(-50%). Sources: web/style.css:1.
- Reduced motion: @media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;animation:none!important;transition:none!important}}. Source: web/style.css:6. CSS motion stops; replay time still advances when started. Touch uses the same native buttons, selects and range input; there is no hover-only action or touch-specific animation path. Dialog and native form controls receive their own clicks; no separate painted interaction surface exists.
- Story scheduling: cps=4.51; margin=20; finish=Math.max(.2,duration-3); each natural sentence duration Math.max(2,[...text].length/4.51); scale=Math.min(1,finish*.84/sum). Scheduling is a virtual character-rate model when sound is off. Source: web/app.js:7-15.
- Playback defaults: mode='replay', language='en', speed=4, sound=false; source switches to recorded when its validated manifest has journeys. Speed buttons are 1×, 4×, 16×; audio sets speed to 1. Sources: web/app.js:4,186-189,385,523-530 and web/index.html:41.
- Clock: requestAnimationFrame tick clamps the per-frame delta to 2 seconds; elapsed increments delta*speed. Audio timeout is duration()+180 seconds. Live polls after 20000 ms when visible. HTTP timeout defaults: /api/plan 90000 ms, /api/write 45000 ms, other paths 25000 ms. Sources: web/app.js:140-151,195,290.
- Logs retain 20 entries; receipts retain 50 entries. Tokens show reported total_tokens or prompt_tokens+completion_tokens; absent tokens, costs and latency remain unreported. Display precision: cost toFixed(6), rounded latency ms. Source: web/app.js:54-61,207-211.
- Line colour mapping: {'2호선':'#727d58','5호선':'#8b7897','7호선':'#8c8951'}. Source: web/app.js:3.
- Measured viewport/composition/hook metrics are outside this source-derived contract; no minimum fill ratio, full-frame animation event, total visible-element limit or universal font count is specified by the existing app.

Additional shell constants: lang=en; UTF-8; width=device-width,initial-scale=1; theme-color #f7f5ee; outline:3px solid #8f791f; outline-offset:4px. Rail interpolation left/width is railFraction*100%; marker transform:translateX(-50%). No separate loader/reveal, no hidden-at-rest content, native touch/keyboard controls; speech feature detection and fallback remain as described in mechanics. No universal composition or promotional animation threshold has been adopted.

### Required copy registry (verbatim)

- Copy verbatim: 'Last Sentence'
- Copy verbatim: 'L'
- Copy verbatim: '·'
- Copy verbatim: '마지막 문장'
- Copy verbatim: 'WORKING PROTOTYPE'
- Copy verbatim: 'A SMALL STORY FOR THE WAY HOME'
- Copy verbatim: 'Every journey deserves'
- Copy verbatim: 'a good ending'
- Copy verbatim: '.'
- Copy verbatim: 'A story that follows your train.'
- Copy verbatim: 'The last sentence is your cue to step out.'
- Copy verbatim: 'Replay'
- Copy verbatim: 'DEMO'
- Copy verbatim: 'Live'
- Copy verbatim: 'SEOUL METRO'
- Copy verbatim: 'Line 2 · 2호선'
- Copy verbatim: 'Line 5 · 5호선'
- Copy verbatim: 'Line 7 · 7호선'
- Copy verbatim: '→'
- Copy verbatim: 'YOUR EXIT'
- Copy verbatim: 'EN'
- Copy verbatim: '한국어'
- Copy verbatim: 'SOURCE'
- Copy verbatim: 'Authored timing fixture'
- Copy verbatim: 'Recorded train observations (unavailable)'
- Copy verbatim: 'JOURNEY'
- Copy verbatim: 'BOARDING AT'
- Copy verbatim: 'Synthetic timing · authored story · no model calls'
- Copy verbatim: 'EXPERIMENTAL LIVE CONNECTION'
- Copy verbatim: 'Connect a train, then a story.'
- Copy verbatim: 'Checking the configured service…'
- Copy verbatim: 'An actual station-arrival observation is required before a forecast.'
- Copy verbatim: 'Your actual train and direction'
- Copy verbatim: 'No live positions loaded'
- Copy verbatim: 'Your exit'
- Copy verbatim: 'Choose an anchored train first'
- Copy verbatim: 'Refresh positions'
- Copy verbatim: 'Start live story'
- Copy verbatim: 'Stop story'
- Copy verbatim: 'Live starts only after a fresh, verified arrival anchor and a validated route ETA. A connected story uses billable model calls. Wall-clock time continues during generation; station observations are not door sensors. Real live inference and arrival accuracy remain unmeasured.'
- Copy verbatim: 'PROLOGUE / A NOTE LEFT BEHIND'
- Copy verbatim: 'Sound off'
- Copy verbatim: 'THE YELLOW ENVELOPE'
- Copy verbatim: '01 / 12'
- Copy verbatim: 'Someone had left a yellow envelope on the seat beside you.'
- Copy verbatim: 'Hand-authored story · synthetic journey'
- Copy verbatim: 'READY WHEN YOU ARE'
- Copy verbatim: 'BEHIND THE STORY'
- Copy verbatim: 'The Conductor'
- Copy verbatim: 'LOCAL PROPOSALS'
- Copy verbatim: 'A local rule proposes scene changes as the known replay clock advances. The authored story stays fixed.'
- Copy verbatim: 'REPLAY TIME LEFT'
- Copy verbatim: '09:20'
- Copy verbatim: 'STORY BUDGET'
- Copy verbatim: '2,435'
- Copy verbatim: 'chars'
- Copy verbatim: 'Designed for Nemotron 3.5 Lightning'
- Copy verbatim: 'Not connected · no model calls in replay'
- Copy verbatim: 'YOUR JOURNEY'
- Copy verbatim: '2'
- Copy verbatim: '강남'
- Copy verbatim: '종합운동장'
- Copy verbatim: 'ONE DIRECTION'
- Copy verbatim: 'FIXTURE ARRIVAL'
- Copy verbatim: 'THE ENVELOPE'
- Copy verbatim: 'A CHANGE OF PLAN'
- Copy verbatim: 'THE LAST SENTENCE'
- Copy verbatim: '↗'
- Copy verbatim: '00:00'
- Copy verbatim: 'Start story'
- Copy verbatim: 'SPEED'
- Copy verbatim: '1×'
- Copy verbatim: '4×'
- Copy verbatim: '16×'
- Copy verbatim: 'Virtual speech clock · text only'
- Copy verbatim: 'FIXTURE SCHEDULE ERROR'
- Copy verbatim: '−3 s'
- Copy verbatim: 'Compared with the synthetic station-arrival event. This is a scheduler check, not measured train or speech performance.'
- Copy verbatim: 'Receipts'
- Copy verbatim: '0 API CALLS'
- Copy verbatim: 'No inference receipts yet.'
- Copy verbatim: 'The replay uses authored text and local rules. Model tokens, cost and latency appear only after real API responses.'
- Copy verbatim: 'Generate with connected models'
- Copy verbatim: 'Return to authored story'
- Copy verbatim: 'Optional billable requests · inference reservation cap ≤ $3; Tavily separate. Account billing may differ.'
- Copy verbatim: 'Read the measurement status'
- Copy verbatim: 'i'
- Copy verbatim: 'An honest replay.'
- Copy verbatim: 'The three routes and stories are authored fixtures. Arrival means a simulated station event; door opening and real-world accuracy have not been measured.'
- Copy verbatim: 'Read the limitations ↗'
- Copy verbatim: 'NO ACCOUNT NEEDED'
- Copy verbatim: 'LAST SENTENCE'
- Copy verbatim: 'SEOUL, 2026'
- Copy verbatim: 'Conductor + Writer'
- Copy verbatim: '/'
- Copy verbatim: 'Built for a better ending.'
- Copy verbatim: 'Service connection'
- Copy verbatim: '×'
- Copy verbatim: 'Replay works without a service. A configured Worker can provide live positions and model receipts.'
- Copy verbatim: 'Worker URL'
- Copy verbatim: 'Session access token'
- Copy verbatim: 'The token stays in this tab’s memory. It is never saved to storage or sent outside the chosen service.'
- Copy verbatim: 'Clear'
- Copy verbatim: 'Save connection'

- Playback labels copy verbatim: 'Start story | Pause | Continue | Play again | Restart story | Sound on | Sound off'
- Available recorded source copy verbatim: 'Recorded train observations'
- Recorded arrival label copy verbatim: 'RECORDED DURATION'
- Scheduler result label copy verbatim: 'REPLAY SCHEDULE ERROR'
- Audio unavailable label copy verbatim: 'AUDIO LANDING ERROR'
- Audio pending label copy verbatim: 'SPEECH END NOT YET OBSERVED'
- Observed speech label copy verbatim: 'SPEECH VS OBSERVATION'
- Fixture speech label copy verbatim: 'BROWSER SPEECH VS FIXTURE'
- No speech engine copy verbatim: 'No browser speech engine is available. Text-only replay uses a virtual clock.'
- Korean authorship notice copy verbatim: '한국어 대본은 사람이 쓴 예시입니다. 실제 한국어 모델 실행은 아직 측정하지 않았습니다.'
- English authorship notice copy verbatim: 'English text is an authored fixture. No Writer model was run.'
- Empty keyless receipt copy verbatim: 'No inference receipts yet.'
- Recorded provenance copy verbatim: 'Recorded observations. '
- Recorded timing limitation copy verbatim: 'The story is authored unless connected models are explicitly used. Provider lag and door-opening offsets are unmeasured. '

### Complete CSS token and component contract

This is the full web/style.css source, with the original cascade and units retained. It fixes every selector-level colour, pixel/rem/em/vw value, font stack, responsive threshold and timing literal, including overrides. Source web/style.css:1-17; SHA-256 5ba58a4cfd50624fc478aadccbaebb4b188bfe28b941cce86cf31ef27e8628b6.

The eyebrow labels use the existing .eyebrow class for the story-intro, Conductor and journey headings. [chosen — ref: web/index.html:20,30,39,41 and web/style.css:1; this reverse-engineered contract preserves the existing labelled panel hierarchy for later designer review.]

The native dialog backdrop uses backdrop-filter:blur(2px). [chosen — why: reproduced from web/style.css:1, where it applies only behind an explicitly opened native connection dialog; it is not an application content surface.]

```css
:root{--paper:#f7f5ee;--card:#fffefa;--ink:#242720;--muted:#797c72;--line:#dfdfd5;--accent:#e4bc39;--accent-soft:#f6edc9;--route:#727d58;--serif:Georgia,'Times New Roman',serif;font-family:Arial,Helvetica,sans-serif;color:var(--ink);background:var(--paper);font-synthesis:none;color-scheme:light}*{box-sizing:border-box}body{margin:0}button,select,input{font:inherit}button,select,a,input[type=range]{-webkit-tap-highlight-color:transparent}button{cursor:pointer}button:disabled,select:disabled{cursor:not-allowed;opacity:.5}button:focus-visible,a:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid #8f791f;outline-offset:4px}button{color:inherit}a{color:inherit}svg{display:block}.shell{max-width:1512px;margin:0 auto;padding:0 64px}.masthead{height:112px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line)}.wordmark{text-decoration:none;display:flex;gap:15px;align-items:center;font-size:23px;letter-spacing:-.8px;font-weight:600}.brand-mark{font-family:var(--serif);font-size:44px;line-height:1;letter-spacing:-10px;padding-right:8px}.brand-mark>span{color:var(--accent);font-size:51px}.wordmark-ko{display:block;font-size:10px;letter-spacing:2px;margin-top:7px;font-weight:400;color:var(--muted)}.masthead-right{display:flex;gap:25px;align-items:center}.prototype-badge{font-size:9px;letter-spacing:1.4px;color:var(--muted);display:flex;align-items:center;gap:8px}.prototype-badge i{display:block;width:5px;height:5px;border-radius:50%;background:#7d8b66}.icon-button{border:1px solid var(--line);border-radius:50%;width:36px;height:36px;display:grid;place-items:center;background:none}.icon-button svg{width:18px;height:18px}.intro-row{display:flex;justify-content:space-between;align-items:flex-end;padding:48px 0 36px}.eyebrow{font-size:9px;letter-spacing:1.7px;font-weight:600;margin:0;color:var(--muted)}h1{font:400 clamp(36px,3.25vw,49px)/1.08 var(--serif);letter-spacing:-1.8px;margin:17px 0 0}.accent{color:#ba9520}.intro-copy{font-size:13px;line-height:1.8;color:var(--muted);margin:0 0 4px;max-width:290px}.journey-controls{display:flex;align-items:center;gap:30px;padding:17px 0 22px;border-top:1px solid var(--line)}.mode-switch{display:flex;border:1px solid var(--line);padding:4px;border-radius:5px;flex-shrink:0;gap:2px}.mode-switch button{border:none;padding:10px 12px;border-radius:3px;background:transparent;font-size:11px;display:flex;align-items:center;gap:8px;color:var(--muted)}.mode-switch button.selected{background:var(--ink);color:#fffefa}.small-pill{font-size:7px;color:var(--accent);letter-spacing:.8px}.live-dot{width:5px;height:5px;border:1px solid currentColor;border-radius:50%;display:inline-block}.route-controls{display:flex;align-items:center;gap:25px;flex:1;min-width:0}.route-controls label{font-size:8px;letter-spacing:1.2px;color:var(--muted);min-width:130px}.route-controls select{display:block;border:0;background:transparent;color:var(--ink);font-size:13px;margin:6px 0 0 -4px;padding:0 20px 0 0;max-width:220px;height:23px}.control-arrow{color:#a3a398;font-size:19px;margin-top:12px}.language-switch{display:flex;border-left:1px solid var(--line);padding-left:22px;gap:4px;flex-shrink:0}.language-switch button{border:0;background:none;color:var(--muted);padding:7px 9px;font-size:10px}.language-switch button.selected{background:#e9e8df;color:var(--ink);border-radius:3px}.workspace{display:grid;grid-template-columns:minmax(0,2.2fr) minmax(270px,1fr);gap:18px}.story-card,.conductor-card,.timeline-card,.receipts-card{border:1px solid var(--line);border-radius:7px;background:var(--card);min-width:0}.story-card{padding:26px 30px 23px;display:flex;flex-direction:column;min-height:360px;position:relative;overflow:hidden}.story-top{display:flex;justify-content:space-between;gap:12px;align-items:center}.chapter-label{font-size:8px;letter-spacing:1.1px;color:var(--muted);display:flex;gap:9px;align-items:center}.yellow-square{width:6px;height:6px;background:var(--accent)}.audio-button{display:flex;gap:7px;align-items:center;border:0;background:none;font-size:10px;color:var(--muted);padding:4px 0;white-space:nowrap}.audio-button svg{width:16px;height:16px}.audio-button[aria-pressed=true]{color:var(--ink)}.story-typography{margin:35px 25px 32px;flex:1;display:flex;flex-direction:column;justify-content:center}.story-meta{display:flex;justify-content:space-between;gap:10px;font-size:8px;letter-spacing:1.7px;color:#96978e;margin:0 0 19px}.story-meta span:last-child{letter-spacing:.5px;font-variant-numeric:tabular-nums}.story-card blockquote{font:400 clamp(26px,2.8vw,40px)/1.27 var(--serif);letter-spacing:-.8px;margin:0;max-width:690px;min-height:104px;overflow-wrap:anywhere}.story-card blockquote[lang=ko]{font-family:Georgia,'Apple SD Gothic Neo','Malgun Gothic',serif;font-size:clamp(26px,2.5vw,36px);letter-spacing:-.7px;line-height:1.45}.sentence-rule{display:flex;gap:5px;margin-top:27px}.sentence-rule span{height:2px;background:#e6e5dc;width:20px}.sentence-rule span:first-child{background:var(--accent);width:36px}.story-foot{display:flex;justify-content:space-between;gap:10px;font-size:9px;color:var(--muted)}.reading-indicator{font-size:7px;letter-spacing:1px;display:flex;align-items:center;gap:6px}.reading-indicator i{width:4px;height:4px;border-radius:50%;background:#989d8e}.reading-indicator.running i{background:#8d9d66;animation:pulse 1.6s infinite}.conductor-card{padding:25px 24px 0;display:flex;flex-direction:column}.panel-heading{display:flex;justify-content:space-between;gap:12px;align-items:center}.panel-heading h2{font-family:var(--serif);font-weight:400;font-size:23px;letter-spacing:-.7px;margin:9px 0 0}.outline-badge{border:1px solid #d7d8cd;padding:5px 6px;border-radius:3px;font-size:7px;letter-spacing:.7px;color:var(--muted);white-space:nowrap}.conductor-explainer{font-size:11px;line-height:1.7;color:var(--muted);margin:15px 0 22px}.budget-row{display:flex;gap:30px;padding-bottom:19px;border-bottom:1px solid #e9e8df}.stat-label{display:block;font-size:7px;letter-spacing:1.1px;color:var(--muted)}.budget-row strong{display:block;font-size:22px;font-weight:400;font-variant-numeric:tabular-nums;letter-spacing:-.6px;margin-top:8px}.budget-row strong small{font-size:9px;letter-spacing:0;color:var(--muted)}.conductor-log{min-height:100px;max-height:145px;overflow:auto;margin:17px 0 15px;flex:1;scrollbar-width:thin}.log-entry{display:grid;grid-template-columns:30px 1fr;gap:7px;margin-bottom:12px;font-size:10px;line-height:1.6}.log-entry time{color:#a2a297;font-size:8px;font-variant-numeric:tabular-nums;margin-top:2px}.log-entry p{margin:0;color:#666a5d}.log-entry:first-child p{color:var(--ink)}.log-entry strong{font-weight:500}.log-operation{background:#f3efd9;color:#8c711a;border-radius:2px;display:inline-block;font-size:7px;padding:1px 4px;margin-left:4px;letter-spacing:.5px}.planned-model{display:flex;gap:7px;align-items:flex-start;padding:14px 0 15px;border-top:1px solid #e9e8df;font-size:8px;color:#777c6b;line-height:1.3}.planned-model small{display:block;font-size:8px;color:#a0a195;margin-top:4px}.planned-dot{width:5px;height:5px;border-radius:50%;background:#a6aa9e;flex-shrink:0;margin-top:2px}.timeline-card{padding:25px 30px 23px}.timeline-header{display:flex;justify-content:space-between;gap:16px}.route-heading{display:flex;align-items:center;gap:10px;margin-top:12px;font-size:13px;line-height:1.2;flex-wrap:wrap}.route-heading>span:nth-child(2)>span{color:#a2a297;margin:0 6px}.line-roundel{width:20px;height:20px;border-radius:50%;display:grid;place-items:center;background:var(--route);color:#fff;font-size:10px}.direction-badge{font-size:6px;color:var(--muted);letter-spacing:1px;border-left:1px solid var(--line);padding-left:10px;margin-left:2px}.arrival-label{text-align:right}.arrival-label strong{display:block;font-size:17px;font-weight:400;font-variant-numeric:tabular-nums;margin-top:9px}.rail-wrap{position:relative;margin:44px 10px 24px}.rail-track{position:absolute;top:4px;left:0;right:0;height:2px;background:#daddd2}.rail-progress{display:block;height:2px;background:var(--route);width:0}.train-marker{position:absolute;top:-25px;left:0;transform:translateX(-50%);width:26px;height:26px;border-radius:5px;background:var(--ink);color:var(--paper);padding:4px;z-index:2;transition:left .15s linear}.train-marker svg{width:18px;height:18px}.station-dots{display:flex;justify-content:space-between;position:relative;z-index:1}.station{flex:0 1 0;text-align:center;position:relative;min-width:0;display:flex;align-items:center;flex-direction:column}.station .dot{display:block;width:10px;height:10px;border:2px solid #c4c9ba;background:var(--card);border-radius:50%;position:relative;z-index:1;flex-shrink:0}.station.visited .dot{border-color:var(--route);background:var(--route)}.station.exit .dot{border-color:#b28e1f;background:var(--accent);box-shadow:0 0 0 4px #f8f0d4}.station .station-name{position:relative;left:0;margin-top:14px;font-size:9px;color:#8d9183;white-space:nowrap;line-height:1.3}.station.visited .station-name{color:var(--ink)}.station.exit .station-name{color:var(--ink);font-weight:600}.exit-caption{display:block;font-size:6px;font-weight:500;letter-spacing:.6px;color:#9c7d1d;margin-top:5px}.scene-bands{display:flex;gap:3px;margin:15px -2px 0}.scene-bands span{font-size:6px;letter-spacing:.8px;color:#939786;flex:1;background:#edeee5;border-radius:2px;text-align:center;padding:6px 2px}.scene-bands span:last-child{background:#f5edcf;color:#9a7c21}.scene-bands i{font-style:normal;margin-left:3px}.scrubber-row{display:flex;gap:11px;align-items:center}.scrubber-row>span{font-size:8px;color:var(--muted);font-variant-numeric:tabular-nums}.scrubber-row input{flex:1;min-width:0;accent-color:#b7952e;height:12px;cursor:pointer}.playback-row{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:18px}.playback-actions{display:flex;align-items:center;gap:8px}.primary-button{display:inline-flex;justify-content:center;align-items:center;gap:9px;background:var(--ink);color:#fffefa;border:1px solid var(--ink);border-radius:4px;padding:11px 15px;font-size:10px;white-space:nowrap}.primary-button svg{width:11px;height:11px;fill:currentColor}.primary-button:hover{background:#414638}.restart-button{display:grid;place-items:center;border:none;background:none;width:30px;height:30px;color:var(--muted)}.restart-button svg{width:16px;height:16px}.speed-control{display:flex;align-items:center;gap:2px}.speed-control>span{font-size:6px;letter-spacing:.7px;color:var(--muted);margin-right:7px}.speed-control button{padding:6px 7px;border:0;background:none;font-size:9px;color:var(--muted);border-radius:3px}.speed-control button.selected{background:#eaece2;color:var(--ink)}.timing-label{font-size:7px;color:#919585;text-align:right;line-height:1.5;max-width:125px;margin:0}.receipts-card{padding:24px;display:flex;flex-direction:column}.receipts-heading{display:flex;align-items:center;justify-content:space-between;gap:10px}.receipts-heading h2{font-size:13px;letter-spacing:-.2px;font-weight:500;margin:0}.receipts-heading>span{font-size:6px;letter-spacing:1px;color:var(--muted)}.receipt-list{flex:1;margin-top:15px;max-height:210px;overflow:auto}.empty-receipts{padding:17px 7px 20px;text-align:center;color:#979c8a}.empty-receipts svg{width:30px;height:30px;margin:0 auto 13px;color:#a5ab97}.empty-receipts p{font-size:10px;color:#747b65;margin:0 0 9px}.empty-receipts small{font-size:9px;line-height:1.7;display:block;max-width:220px;margin:auto}.text-link{text-decoration:none;color:#737a64;font-size:8px;display:flex;justify-content:space-between;gap:10px;border-top:1px solid #e9e8df;padding-top:14px}.text-link:hover{text-decoration:underline}.receipt{border-bottom:1px solid #e9e8df;padding:9px 0;font-size:8px;line-height:1.7}.receipt strong{font-weight:500;display:block;overflow-wrap:anywhere}.receipt small{display:flex;gap:8px;flex-wrap:wrap;font-size:8px;color:var(--muted)}.provenance-strip{margin:20px 0 35px;display:flex;align-items:center;gap:11px;color:var(--muted)}.provenance-symbol{display:grid;place-items:center;width:15px;height:15px;border:1px solid #b4b8a8;border-radius:50%;font:italic 10px var(--serif);flex-shrink:0}.provenance-strip p{font-size:9px;line-height:1.7;margin:0;max-width:880px}.provenance-strip strong{font-weight:500;color:#656d57}.provenance-strip a{color:#747b66;text-underline-offset:3px;white-space:nowrap}.strip-tag{margin-left:auto;font-size:6px;letter-spacing:1.2px;white-space:nowrap;padding-left:18px}footer{border-top:1px solid var(--line);display:flex;justify-content:space-between;gap:15px;padding:22px 0 27px;font-size:7px;letter-spacing:1.2px;color:#969b89}.footer-dot{padding:0 8px;color:#b0b49e}.notice{font-size:11px;line-height:1.6;background:#f2e9ca;border:1px solid #e3d5a8;border-radius:4px;padding:12px 16px;margin:0 0 17px;color:#7d6729}.live-panel{background:var(--card);border:1px solid var(--line);padding:24px;border-radius:6px;margin:0 0 18px;display:grid;grid-template-columns:1fr 1fr;gap:20px}.live-panel[hidden],.notice[hidden],.landing-result[hidden]{display:none}.live-panel h2{font:400 24px var(--serif);margin:10px 0}.live-panel p{font-size:11px;color:var(--muted);line-height:1.7;margin:0}.live-actions{display:flex;gap:10px;align-items:flex-end;min-width:0}.live-actions label{font-size:9px;color:var(--muted);flex:1;min-width:0}.live-actions select{display:block;margin-top:7px;width:100%;background:var(--paper);border:1px solid var(--line);font-size:11px;padding:10px;border-radius:4px}.secondary-button{font-size:10px;padding:11px 13px;border-radius:4px;border:1px solid var(--line);background:transparent;white-space:nowrap}.live-panel .live-disclosure{grid-column:1/-1;border-top:1px solid var(--line);padding-top:13px;font-size:9px}.landing-result{display:flex;gap:20px;align-items:center;border-top:1px solid var(--line);padding-top:20px;margin-top:22px}.landing-result strong{font:400 35px var(--serif);display:block;margin-top:5px;white-space:nowrap}.landing-result p{font-size:9px;color:var(--muted);line-height:1.7;max-width:340px;margin:0}dialog{border:1px solid var(--line);background:var(--paper);color:var(--ink);border-radius:9px;width:min(470px,calc(100% - 32px));padding:27px;box-shadow:0 20px 100px #1c241523}dialog::backdrop{background:#1a201c66;backdrop-filter:blur(2px)}.dialog-head{display:flex;align-items:center;justify-content:space-between;gap:16px}.dialog-head h2{font:400 26px var(--serif);margin:0}dialog p{font-size:12px;line-height:1.7;color:var(--muted);margin:18px 0}dialog label{display:block;font-size:10px;margin:18px 0;color:#737a64}dialog input{display:block;border:1px solid var(--line);border-radius:4px;background:var(--card);color:var(--ink);width:100%;padding:12px;margin-top:7px;font-size:12px}dialog small{font-size:10px;line-height:1.7;display:block;color:var(--muted)}.dialog-actions{margin-top:25px;display:flex;gap:10px;justify-content:flex-end}@keyframes pulse{50%{opacity:.25}}
@media(min-width:1450px){.shell{padding:0 78px}.story-card{min-height:375px}.intro-row{padding-top:52px;padding-bottom:42px}.story-typography{margin-top:40px;margin-bottom:40px}}
@media(max-width:1100px){.shell{padding:0 38px}.journey-controls{gap:20px}.route-controls{gap:13px}.route-controls label{min-width:105px}.route-controls select{max-width:175px}.workspace{grid-template-columns:minmax(0,1.9fr) minmax(250px,1fr);gap:14px}.story-card,.timeline-card{padding-left:24px;padding-right:24px}.story-typography{margin-left:10px;margin-right:10px}.story-card blockquote{font-size:33px}.conductor-card{padding-left:19px;padding-right:19px}.receipts-card{padding:20px}.playback-row{flex-wrap:wrap}.timing-label{max-width:none;text-align:left;width:100%}.story-foot{font-size:8px}.reading-indicator{font-size:6px}.budget-row{gap:23px}.strip-tag{display:none}.direction-badge{display:none}}
@media(max-width:780px){.shell{padding:0 24px}.masthead{height:87px}.wordmark{font-size:20px}.brand-mark{font-size:39px}.wordmark-ko{font-size:8px}.prototype-badge{font-size:7px;letter-spacing:1px}.masthead-right{gap:13px}.intro-row{padding:33px 0 27px}.intro-copy{font-size:11px;max-width:190px}h1{font-size:39px;letter-spacing:-1.5px}.journey-controls{gap:14px;flex-wrap:wrap}.mode-switch{order:0}.language-switch{order:1;margin-left:auto;padding-left:0;border:0}.route-controls{order:2;flex-basis:100%;justify-content:space-between;border-top:1px solid var(--line);padding-top:15px;margin-top:2px}.route-controls label{flex:1}.route-controls select{max-width:100%}.control-arrow{margin-right:25px}.workspace{grid-template-columns:minmax(0,1.6fr) minmax(230px,1fr)}.story-card{grid-column:1/-1;min-height:330px}.story-typography{margin:30px 35px}.story-card blockquote{font-size:36px;min-height:100px}.conductor-card{grid-column:2;grid-row:2/4}.timeline-card{grid-column:1;grid-row:2/3}.receipts-card{grid-column:1;grid-row:3/4}.receipts-card .empty-receipts{padding:10px 0 12px;text-align:left;display:grid;grid-template-columns:25px 1fr;gap:0 12px}.empty-receipts svg{width:24px;height:24px;grid-row:1/3;margin:3px 0}.empty-receipts small{max-width:none;margin:0;font-size:8px}.empty-receipts p{margin:0 0 5px}.receipt-list{margin-top:10px}.route-heading{font-size:11px;gap:7px}.timeline-card{padding:22px 17px}.rail-wrap{margin-left:4px;margin-right:4px}.station .station-name{font-size:7px}.scene-bands span{font-size:5px;letter-spacing:.2px}.arrival-label strong{font-size:14px}.arrival-label .stat-label{font-size:6px}.speed-control>span{display:none}.playback-row{gap:8px}.primary-button{padding:10px 12px}.provenance-strip{align-items:flex-start;margin-bottom:25px}.provenance-symbol{margin-top:3px}.provenance-strip p{font-size:8px}footer{font-size:6px;letter-spacing:.6px}.landing-result{flex-direction:column;align-items:flex-start;gap:10px}.live-panel{grid-template-columns:1fr}.live-actions{flex-wrap:wrap}.live-actions select{max-width:100%}}
@media(max-width:540px){.shell{padding:0 18px}.masthead{height:78px}.wordmark{font-size:19px;gap:10px}.brand-mark{font-size:35px;letter-spacing:-8px}.brand-mark>span{font-size:43px}.wordmark-ko{letter-spacing:1.4px;margin-top:5px;font-size:7px}.prototype-badge{display:none}.icon-button{width:31px;height:31px}.intro-row{padding-top:27px;padding-bottom:25px;display:block}.intro-copy{margin-top:18px;max-width:none;font-size:11px;line-height:1.6}.intro-copy br{display:none}.intro-copy br:after{content:' '}h1{font-size:36px;letter-spacing:-1.4px;margin-top:13px}.eyebrow{font-size:7px;letter-spacing:1.4px}.journey-controls{padding-top:14px;padding-bottom:18px}.mode-switch button{font-size:10px;padding:8px 10px}.language-switch button{font-size:9px;padding:6px 8px}.route-controls{gap:12px;padding-top:12px}.route-controls label{font-size:7px;min-width:0}.route-controls select{font-size:12px;max-width:160px}.control-arrow{margin-right:10px}.workspace{grid-template-columns:minmax(0,1fr);gap:13px}.story-card{grid-column:1;grid-row:1;min-height:329px;padding:20px}.story-typography{margin:30px 6px 28px}.story-card blockquote{font-size:31px;line-height:1.28;min-height:118px;letter-spacing:-.65px}.story-card blockquote[lang=ko]{font-size:28px;min-height:118px}.chapter-label{font-size:6px;letter-spacing:.7px;gap:7px}.audio-button{font-size:8px;gap:5px}.audio-button svg{width:14px;height:14px}.story-meta{font-size:7px;letter-spacing:1.2px;margin-bottom:15px}.sentence-rule{margin-top:23px}.story-foot{font-size:7px;align-items:center}.reading-indicator{font-size:5px;gap:4px;letter-spacing:.7px}.timeline-card{grid-column:1;grid-row:2;padding:22px 20px}.conductor-card{grid-column:1;grid-row:3;padding:23px 22px 0;min-height:350px}.receipts-card{grid-column:1;grid-row:4;padding:22px}.receipts-card .empty-receipts{padding:16px 0 18px}.empty-receipts small{font-size:9px;max-width:260px}.receipt-list{max-height:230px}.budget-row{gap:50px;padding-bottom:17px}.conductor-log{max-height:135px;min-height:110px}.conductor-explainer{font-size:11px;max-width:300px;margin-bottom:19px}.panel-heading .eyebrow{font-size:7px}.panel-heading h2{font-size:25px}.log-entry{font-size:11px;grid-template-columns:33px 1fr}.log-entry time{font-size:8px}.planned-model{font-size:9px;padding-top:15px;padding-bottom:17px}.planned-model small{font-size:8px}.route-heading{font-size:12px}.arrival-label strong{font-size:16px}.station .station-name{font-size:8px}.rail-wrap{margin-top:42px;margin-bottom:24px}.scene-bands span{font-size:5px;letter-spacing:.4px}.playback-row{flex-wrap:nowrap;position:relative;margin-bottom:22px}.timing-label{position:absolute;bottom:-23px;left:0;font-size:7px}.speed-control{gap:1px}.speed-control button{font-size:9px;padding:6px}.primary-button{font-size:10px;padding:11px 13px}.landing-result{flex-direction:row;gap:16px;margin-top:36px}.landing-result strong{font-size:31px}.landing-result p{font-size:8px}.provenance-strip{margin-top:20px}.provenance-strip p{font-size:8px;line-height:1.8}.provenance-strip a{white-space:normal}footer{display:block;font-size:6px;padding-top:20px;line-height:2.3}footer>span{display:block}.live-panel{padding:20px;gap:15px}.live-panel h2{font-size:23px}.live-actions{display:block}.live-actions button{margin-top:10px}.live-panel p{font-size:10px}dialog{padding:23px}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;animation:none!important;transition:none!important}}

.source-controls{display:flex;align-items:center;gap:24px;border-top:1px solid var(--line);padding:13px 0 18px;margin-top:-3px}.source-controls label{font-size:7px;letter-spacing:1px;color:var(--muted);min-width:0}.source-controls select{display:block;border:none;background:transparent;color:var(--ink);font-size:10px;margin:6px 0 0 -3px;max-width:270px;padding-right:17px;height:20px}.source-controls p{margin:7px 0 0 auto;color:#969b88;font-size:8px;line-height:1.6;max-width:290px}.model-actions{margin:7px 0 15px}.model-actions .secondary-button{width:100%;font-size:9px;padding:10px 6px}.model-actions small{display:block;font-size:7px;line-height:1.7;color:var(--muted);margin-top:8px}.text-button{display:block;background:none;border:0;text-decoration:underline;text-underline-offset:3px;font-size:8px;color:var(--muted);padding:10px 0 0}.text-button[hidden]{display:none}.model-active .outline-badge{border-color:#c7ccba;color:#64704e}.model-active .planned-dot{background:#7a8a5b}.generated-label{color:#5e6f45}
@media(max-width:780px){.source-controls{gap:18px;flex-wrap:wrap;padding-top:12px}.source-controls p{width:100%;max-width:none;margin:-4px 0 0}.source-controls select{max-width:250px}.source-controls label{flex:1}.receipts-card .model-actions .secondary-button{font-size:8px}}
@media(max-width:540px){.source-controls{gap:13px}.source-controls label{max-width:calc(50% - 7px)}.source-controls select{font-size:9px;max-width:100%;min-width:0}.source-controls p{font-size:7px}.model-actions small{font-size:8px}.receipts-card .model-actions .secondary-button{font-size:10px}}

.source-controls[hidden],.route-controls label[hidden],.control-arrow[hidden],.model-actions button[hidden],.live-buttons button[hidden]{display:none}.live-actions{display:grid;grid-template-columns:1fr 1fr;gap:12px}.live-buttons{display:flex;gap:8px;grid-column:1/-1;flex-wrap:wrap}.live-panel .live-forecast{font-size:13px;color:#636f50;margin-top:12px}.live-panel .live-disclosure{font-size:9px}.live-estimated{color:#718352}.live-arrival{border-color:#c8cfb7;background:#eff2e8}.live-panel .live-actions label{min-width:0}.live-panel .live-actions select{font-size:10px;padding:9px;min-width:0}.live-model-status{font-size:8px;color:var(--muted)}
@media(max-width:780px){.live-actions{grid-template-columns:1fr 1fr}}
@media(max-width:540px){.live-actions{display:grid;grid-template-columns:1fr;gap:10px}.live-buttons{grid-column:1;gap:8px}.live-buttons button{margin-top:0}.live-panel .live-forecast{font-size:12px}}

.scene-bands span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
@media(max-width:540px){.source-controls{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:13px 16px;align-items:start}.source-controls label{max-width:none;min-width:0}.source-controls select{width:100%;max-width:100%;font-size:10px}.source-controls p{width:auto;max-width:none;margin:12px 0 0;font-size:7px;line-height:1.7}}
```

## Assets

ASSET_BASE_URL = web/

All visible icons and the brand mark are inline markup in index.html; fonts resolve from the system. There are no separate raster, vector-file, media, downloaded font or GPU model assets. None — fully procedural visible artwork; the following source/data files are runtime inputs, not artwork.

| File | Role | Local path |
| --- | --- | --- |
| index.html | Native controls, initial sentence, inline SVG and fallback disclosures | index.html |
| style.css | Complete component and breakpoint definitions | style.css |
| app.js | Replay, connected-state, speech and receipt orchestration | app.js |
| replay/manifest.json | Explicitly synthetic timing fixtures | replay/manifest.json |
| replay/recorded-manifest.json | Recorded observation windows with known replay clocks | replay/recorded-manifest.json |

The Assets gate's extension matcher does not verify HTML/CSS/JS/JSON files. They were read as local source files for this spec; their snapshot hashes are:

| File | SHA-256 |
| --- | --- |
| index.html | b3a388502572485ca973292c733f3eaaaa5ea04c210490261a7e02a76e6286c0 |
| style.css | 5ba58a4cfd50624fc478aadccbaebb4b188bfe28b941cce86cf31ef27e8628b6 |
| app.js | bdf06588c2002088255aa4d219d2bb5410449bb1e1e5951d28207a55f7940cae |
| replay/manifest.json | 92bd6b7e42c4fcc838bb984bbe4b679b55f000e17e9b93a602f84e8a8a501937 |
| replay/recorded-manifest.json | 3a72ff7584b62bec87773de0d1c7744bc13c4d5c3614015bb91f094584ebd169 |

## Open for the designer (not constants)

The designer may propose changes to first-viewport layout, type scale, colour tokens, mobile composition and empty/loading/error-state presentation. This section opens those visual choices for review; it does not silently change the constants recorded above. Record any accepted change as a dated correction with source changes and a new snapshot hash.

The fixed behavior contracts are playback and clock semantics, sentence-boundary application/cancellation, the distinctions between synthetic/recorded/Live and authored/model-generated text, receipt-v2 model identity and usage provenance, explicit missing/unknown costs, model-role labels, billable-action disclosure, and honest ETA/speech/door-timing limitations. Keep controls' accessible names and required limitation semantics when changing presentation. Do not turn virtual-clock schedule errors into measured train, speech, model or door-performance claims.
