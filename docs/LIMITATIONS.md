# Limitations

This is a local prototype. Replay can use real provider observations or explicitly synthetic fixtures, with hand-authored text until connected generation is selected. The current run does not demonstrate real Nemotron output, Tavily use, an observed rider experience, or deployment.

| Area | Boundary |
| --- | --- |
| Arrival | Seoul position records expose station/status and provider receipt time. They do not timestamp doors opening. Recorded arrival is a station-arrival proxy, with polling and provider delay. |
| Timing | Silent replay uses a virtual clock and estimated sentence durations. An audio `end` event, when available, measures browser speech completion, which is still different from doors opening. Speed changes and seeking invalidate a continuous audio timing measurement. |
| ETA | The service requires a completed recording and the registered held-out median-error gate, with at least ten windows and two train identities. Windows overlap and are not independent samples. This is an experimental readiness check, not a confidence interval or an error guarantee. Unknown routes remain unavailable; unseen directed segments disclose a line-median fallback. |
| Data coverage | The current real recording is line 2 only. Line 5/7 replay journeys are fixtures. Their presence in a picker is not evidence of recorded coverage. No other lines are supported. |
| Seoul quota | The official guide states a 1,000-request daily real-time cap. The prepared Worker reserves up to 950 upstream requests per KST day using an atomic counter, then forces replay. A shared key's other applications or local recorders also consume its quota; this app cannot count those requests. |
| Sample key | The current sample call requests at most five trains. Results can change identity between polls and cannot reliably follow every train. |
| Data page | The October 30 HTML includes: “해당 데이터는 종료된 서비스입니다”. Separately, the sample endpoint returned fresh position records. A source-page banner is retained as a service-availability risk; no guarantee of continuity is made. |
| Language | Ultra's supported-language list includes Korean. The inspected Super/Nano/Lightning lists do not. That absence does not prove inability. Korean quality and model obedience remain unmeasured. |
| Speech | Web Speech voices, pronunciation, speed and lifecycle vary by browser/device. No suitable voice means text-only mode. No Korean voice must not silently become a Korean-language quality result. |
| Background use | Keep the screen open and the page active. Wake Lock is best effort, requires a supported secure context and can be released by the browser. This build does not implement geolocation; background restrictions are not attributed to geolocation. |
| Inference | Model IDs and catalog prices were checked publicly. Tool calls, JSON fallback, `reasoning_effort`, latency, token usage and sentence obedience have only mock tests until authenticated execution. |
| Cost | A planning ceiling is not an invoice. Actual token-price estimates require complete provider usage; failures or missing usage cannot be reported as zero-cost successful calls. |
| Live mode | The prepared controller requires selection of the actual train/direction, a fresh server-verified arrival-status anchor and an eligible forward exit. Initial estimates cover 3–10 station segments on the line-2 main loop only. The last 1–2 segments are outside that evaluated horizon and remain experimental. Actual live narration, rider operation and model/TTS landing performance have not been field-tested. |
| Worker transport | The public HTTP sample worked, while a separate HTTPS probe timed out after 20 seconds. Only the published SAMPLE key may use the bounded HTTP fallback; each upstream attempt consumes quota. Private Seoul keys are restricted to HTTPS, whose reachability remains unverified here. |
| Audience | No rider interviews, demand test, accessibility study or field validation was performed. Avoid relying on this prototype as an exit alarm. |

The prior simulation figures in the supplied handoff were not reproduced and are not imported as results. See [RESULTS.md](RESULTS.md).
