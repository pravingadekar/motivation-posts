# Daily agent: "Motivational guru" AI podcast reel (Hindi)

One reel per day: the same fictional AI woman podcaster (character/host.png) speaks a ~25-second Hinglish
motivation talk with lip-synced voice (Gemini Omni), with bold captions. Posted once a day to YouTube Shorts,
Facebook Reels and Instagram Reels through Metricool.

Work autonomously; nobody will reply. Only touch this repository.

## Hard rules
- Metricool: use ONLY brand/blogId **7889447** ("Motivational guru") for every call. The same account holds other
  businesses (7732528 Trade With Captain Pravin, 7773083 CoatCraft Solutions, 7793667 Golu Bandar Kids): never
  create, update or modify anything on them.
- IST = UTC+5:30. The sandbox clock is UTC; compute today's IST date and time from `date -u`.
- Never print, echo or log GEMINI_API_KEY or ELEVENLABS_API_KEY or any part of them.
- Before committing: `git config user.name 'Motivational Guru' && git config user.email pravingadekar05@gmail.com`
- Video budget: at most **6** `genai.py video` calls per day (3 shots + up to 3 retakes). Never loop beyond that.
- Content rules: original lines only. Never attribute quotes to real people, no religion, politics, caste,
  medical or money promises, no hate or shaming, nothing sexual. Warm, positive, practical. Fictional AI host:
  every post is labelled AI-generated on each platform.

## Steps
1. `pip install -r requirements.txt -q`. Compute today's IST date `D` (YYYY-MM-DD).
2. Duplicate check: if `daily/D/posted.txt` exists, or `getScheduledPosts` for brandId 7889447 (today, +05:30)
   already shows a post for today, stop and report "already done".
3. Topic: the first entry in topics.md whose number is not in history.md (after #40, wrap around and give the
   topic a fresh angle).
4. Write `daily/D/script.json` (see the docstring of tools/reel.py):
   - `hook`: on-screen hook, Hinglish, max 7 words, curiosity or emotion ("Ye video tumhare liye hai").
   - exactly **3 shots**; each `dialogue` is one natural spoken Hinglish line in Roman script, **14-20 words**,
     2-3 short sentences, simple everyday Hindi (Indian audience, 18-35). Mark 1-2 key words per shot with `*stars*`.
     No double quotes, no emojis, no numerals (write numbers as words).
   - Shot 1 = strong hook that names the viewer's pain ("Agar log tumhe kamzor samajhte hain..."),
     shot 2 = the turn / truth, shot 3 = payoff line + soft CTA ("...Agar ye baat dil ko chhu gayi, toh follow karo.").
5. Check `[ -n "$GEMINI_API_KEY" ] && echo SET || echo MISSING` (never print the value).
   - SET: `python tools/reel.py prompts daily/D` then `python tools/reel.py clips daily/D`.
     If one shot fails (HTTP error or no video), retry only that shot (within the budget).
   - MISSING (or every Gemini call fails with an auth/billing error): fallback
     `python tools/reel.py still daily/D` (slow zoom on character/host.png, captions and music, no voice),
     skip step 6's voice checks, and say in the final report that the fallback was used.
6. `python tools/reel.py build daily/D`. Open `daily/D/check/*.jpg` and look at each:
   same woman as character/host.png, podcast studio, no garbled on-screen text from the model, captions readable.
   Also check the build output: each shot's speech should be at least 4 s. If a shot is wrong (different person,
   text in frame, cut-off speech), delete `daily/D/clips/shotN.mp4`, re-run `clips` and `build` (within budget).
   If it still fails, do not post; explain in the final report.
7. Write `daily/D/captions.md`:
   - `YT title:` max 90 characters, Hinglish, emotional, ends with `#shorts`.
   - `Caption:` 2-3 short lines (Hinglish, may use a couple of emojis), then the line
     `AI generated video | Motivational guru`, then 12-15 hashtags mixing Hindi/Indian motivation tags
     (#motivation #hindimotivation #motivationalquotes #successmindset #lifelessons #selflove #podcast
     #aipodcast #reels #trending #inspiration #hindiquotes ...).
   - `YT tags:` 8-12 tags.
8. Commit `daily/D` (script.json, prompts, reel.mp4, check, captions.md, timings.json), `git pull --rebase`, push to
   main. Verify `https://raw.githubusercontent.com/pravingadekar/motivation-posts/main/daily/D/reel.mp4` returns 200
   (`curl -sI`). If not, do not schedule.
9. Time: call `getBestTimeToPostByNetwork` for instagram (brand 7889447) for today; pick the best hour between
   18:00 and 22:00 IST that is at least 45 minutes from now. If that fails or nothing qualifies, use 19:30 IST
   (or now + 45 min if later than 19:30). Use the same time for all three networks.
10. `createScheduledPost` once, blogId 7889447, providers youtube + facebook + instagram, the reel's raw URL in
    `media`, `autoPublish: true`, `draft: false`, publicationDate {dateTime, timezone "Asia/Calcutta"}, text = Caption.
    - youtubeData: {title, type "short", privacy "public", madeForKids false, category "PEOPLE_BLOGS",
      tags, isAiGeneratedContent true}
    - facebookData: {type "REEL", title: YT title without "#shorts"}
    - instagramData: {type "REEL", showReelOnFeed true, isAiGenerated true}
11. Write `daily/D/posted.txt` (time and Metricool post id), append `D | #topic | hook | time` to history.md,
    commit and push.
12. Final report: topic, hook, the three lines, post time, Metricool id, retakes used, anything that failed.
