# Natural look test (draft, 14 Nov 2026)

Goal: the host should look like a real person speaking calmly from home, not a glam AI model.
Reference that inspired it: a "girl next door" style Hindi talk reel (simple kurta, soft warm light, close-up, one angle).
We do NOT copy that person's face. Same fictional host, new natural style. The AI label stays on every post.

## 1. Host image prompt (9:16, one image used for all 3 shots)

Photorealistic vertical 9:16 photo, shot on a phone-style 35 mm lens, of a fictional young Indian woman about 25 years
old, sitting in a simple, cozy home corner and talking into a black podcast microphone placed low at the bottom-left
of the frame (it does not cover her face). Same face and long dark-brown hair as the reference, hair loosely tied back
with a few strands falling near her face. She wears a simple off-white cotton kurta with a small pastel floral print,
full or three-quarter sleeves, a thin gold chain and small pearl earrings. Very light everyday makeup, no lipstick
shine, no bindi needed. Natural skin texture with tiny pores and slight unevenness, not airbrushed, not glossy.
Calm, kind, slightly serious expression, mouth relaxed, looking straight into the camera like she is talking to one
friend. Background: plain warm beige wall, a softly blurred green plant on the left, warm late-afternoon window light
from the right, soft shadows, muted natural colours (not saturated). Close-up framing: face and shoulders fill the
upper two thirds, mic edge visible at the bottom. Eye-level camera, shallow depth of field. Not resembling any real or
famous person. No text, no logos, no watermark.

### What changes vs. now
| | Now | Natural test |
|---|---|---|
| Outfit | Glam sleeveless saree / tops | Simple cotton kurta, sleeves |
| Skin | Smooth, glossy | Natural texture |
| Light | High-key bright, ring light | Soft warm window light, muted colours |
| Framing | 3 angles with cuts | 1 close-up angle for all 3 shots (feels like one take) |
| Expression | Big, open-mouth | Calm, eye contact |

## 2. Video prompt tone (add to each shot)

"She speaks slowly and softly, like a heart-to-heart talk with a close friend, small natural head movements, normal
blinking, minimal hand movement, no exaggerated mouth or eyebrow movement. Camera locked, very slight handheld feel."

## 3. Sample script, topic #6 (Overthinking band karo, action lo)

One continuous talk, split into 3 parts of about 8 seconds each (same angle, so the cuts feel invisible).

- On-screen hook (small, bottom, Devanagari): **मेरी ये बात सुन कर जाओ**
- Hook (Roman, for logs): Raat ko neend nahi aati? Ye suno

| Shot | dialogue (captions) | dialogue_hi (spoken) |
|---|---|---|
| 1 | Raat ko do baje bhi dimaag wahi *baat* ghuma raha hai na, main samajhti hoon. | रात को दो बजे भी दिमाग वही बात घुमा रहा है ना, मैं समझती हूँ। |
| 2 | Par sach ye hai, sochne se *raasta* nahi banta, ek chhota kadam uthane se banta hai. | पर सच ये है, सोचने से रास्ता नहीं बनता, एक छोटा कदम उठाने से बनता है। |
| 3 | Kal subah bas ek *kaam* karna. Aur ye video us dost ko bhejo jo bahut sochta hai. | कल सुबह बस एक काम करना। और ये वीडियो उस दोस्त को भेजो जो बहुत सोचता है। |

Why this sounds more real: it starts in the middle of a feeling ("main samajhti hoon"), talks to ONE person, uses a
specific moment (raat ke do baje), and ends with one tiny action instead of a big quote.

## 4. Caption style for the test

- Remove the big yellow top box and the big all-caps word captions.
- One small Devanagari hook line near the bottom for the first 3 seconds.
- Clean sentence-case subtitles (white, thin shadow), lower third, 2 lines max.

## Result (14 Nov)
- Canva generate-image with reference MAHaCoi1S1k -> new image Canva media **MAHa2zLSMyI** (944x1680).
- Small preview saved as character/host_natural_preview.png (full size stays in Canva uploads).
- ChatGPT (Chrome, reference host_curvy.png, same prompt) -> character/host_natural_chatgpt.png (768x1365,
  captured from a 941x1672 original as 3 screenshot tiles because downloads do not work). Looks the most real.
- Pravin did not like it and shared a screenshot of the style he wants. v2 (ChatGPT, text-only prompt, NO reference
  photo of that creator, new fictional face): character/host_natural_v2.png. Style: soft round face, hair pulled back
  with side rope braids, pearl hoops, cream floral embroidered kurta, warm airy home background, big warm smile.

- Test reel (14 Nov): daily/test-2026-11-14-natural/reel.mp4, 3 Flow clips (Veo 3.1 Fast, frames mode, start frame
  host_natural_v2.png, same angle) with the new "voice note to a friend" voice prompt in prompts/shotN.txt.
  60 credits used, 76 left until 5 Dec. Old big captions still used. Not posted.
- Flow download note: Chrome saves the clip as a short-lived *.tmp in Downloads; copy only a NEW .tmp right after
  clicking Download (old hidden .tmp files there are other videos).

## Cost if approved
- 1 new host image (Canva/ChatGPT, no Flow credits)
- 3 Flow clips, about 60 credits
