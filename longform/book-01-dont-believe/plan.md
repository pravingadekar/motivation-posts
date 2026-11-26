# Book Summary #1: plan

**Book:** *Don't Believe Everything You Think*, Joseph Nguyen (2022)
**Kyon ye book:** overthinking aur raat ko chalne wala dimaag hi Meera ke sabse achhe Shorts ka topic hai (18, 19, 20 Nov), aur Book Peak par chinta/anxiety wali books sabse zyada chali (Unwinding Anxiety 10 lakh, Don't Worry 136K).

## Format (Meera sirf Shorts mein rahegi)
- 16:9, **18–22 min**, narrator Sarvam **anand_hi_documentary** (Bulbul v4 Flash, pace 1.1); Pravin ne 26 Nov ko samples sunke chuna. Book Peak ki hit videos bhi 17–24 min ki hain.
- Visuals: ChatGPT illustrations. Har lesson ke shuru mein ek title card. `tools/story_video.py` se Ken Burns aur soft music, jaisa "दो दोस्त" mein kiya tha.
- Paise: Sarvam par ~16,000 characters, yaani ~Rs 50. **Flow credits nahi lagenge.**
- Lambai ka hisaab: ratan ek second mein ~13.5 character bolta hai. 20 min ke liye ~110 lines aur ~35–40 images chahiye (ek image 2–4 lines tak chal sakti hai).

## Rules (book summary ke liye)
- Book ke ideas **apne shabdon mein** honge. Book ki koi line copy ya translate nahi hogi, aur author ke munh mein koi quote nahi daalenge.
- Har idea ke saath **apni desi misaal** hogi, taaki video original lage aur YouTube ka "reused content" wala risk kam ho.
- Book aur author ka credit description mein dena hai, aur video mein ek baar bolna hai ("is book mein likha gaya hai ki..."). Video ko official ya author se approved nahi batana.
- Real log, dharm, paisa kamane ke vaade aur kisi ko sharminda karna: ye sab nahi chalega (purana rule).

## Video ka dhaancha
| # | Hissa | Samay | Kya hoga | Misaal / scene |
|---|---|---|---|---|
| 0 | **Hook** | 0:00–0:45 | "Raat ke 2 baj rahe hain. Body thaki hai, par dimaag ek court chala raha hai…" Wada: "is video ke end tak tum jaanoge ki dimaag ko band kaise karte hain, bina zor lagaye." | Ladka bed par, chhat ko ghoor raha hai, phone ki roshni |
| 1 | Book ka parichay | 0:45–1:30 | Book ka naam, ye kis ke liye hai, aage 7 baatein aayengi | Book jaisi illustration (asli cover) |
| 2 | **Baat 1: Khayal aana vs khayal ko chabana** | ~2.5 min | Khayal apne aap aate hain, wo galti nahi. Dukh tab shuru hota hai jab hum use pakad ke baar-baar chabate hain. | Boss ka message "kal baat karte hain" aur raat bhar ki kahani |
| 3 | **Baat 2: Dukh baat se nahi, sochne se** | ~2.5 min | Ek hi ghatna se do log alag mehsoos karte hain. Farak ghatna mein nahi, uske baad ki soch mein hai. | Do dost, ek jaisa result, alag reaction |
| 4 | **Baat 3: Feelings dashboard ki light hain** | ~2.5 min | Bura lagna ek signal hai ki main abhi bahut soch raha hoon. Ye zindagi ke baare mein faisla nahi hai. | Bike ki fuel light: light ko nahi todte |
| 5 | **Baat 4: Shanti tumhara default hai** | ~2.5 min | Shanti kamaani nahi padti. Soch ki mitti baith jaaye to shanti apne aap dikhti hai. | Ganda paani glass mein: hilana band karo, mitti neeche baith jaati hai |
| 6 | **Baat 5: Har khayal solve karna zaroori nahi** | ~2.5 min | Har notification ka jawab nahi dete. Kuch khayal bas aate-jaate hain. | WhatsApp group ke 300 unread |
| 7 | **Baat 6: Zor se nahi, halke mann se kaam** | ~2.5 min | Dabaav wala motivation do din chalta hai. Shaant dimaag se acche idea aate hain. | Har Monday naya plan (Meera ke Short se link) |
| 8 | **Baat 7: Aaj raat ka 5 minute ka abhyas** | ~2.5 min | 1) khayal ko naam do ("ye phir aa gaya"), 2) ek line likh ke "kal subah" bolo, 3) saans par dhyaan, chhat nahi | Notebook, table lamp, "कल सुबह" likha hua |
| 9 | Saar + CTA | 1:30 | 7 baatein ek line mein. "Comment karo: tumhari raat 2 baje wali baat kaunsi hai?" Agli book ka naam. | Subah ki roshni, wahi ladka shaant |

## Packaging (YouTube pehle)
- **Title:** रात को दिमाग चलता रहता है? ऐसे बंद करो | Don't Believe Everything You Think Book Summary in Hindi
- **Thumbnail text:** "सोचना बंद करो" (3 shabd, bade). Image: ladka raat ko bed par aankh khole, sir ke upar uljhe dhaage. Book ka asli cover laga sakte hain.
- **Description:** pehli 2 lines mein fayda, phir 7 baaton ke timestamps, phir book ka credit aur "AI voice aur illustrations" ki line.
- **Time:** shaam 20:00 IST. Overthinking dekhne wale log raat ko active rehte hain, aur hamare Shorts bhi raat ko chale.
- **Facebook:** wahi video FB par type VIDEO mein (priority 2). **Instagram:** 60 s ka trailer reel, hook wala hissa (priority 3).

## Shorts → long video ka pull
- Video se 2 Shorts kaatne hain: Baat 4 (ganda paani) aur Baat 8 (5 min ka abhyas). Har ek mein pinned comment ho: "poori video 👉 link".
- Meera ke purane overthinking Shorts (19 aur 20 Nov) par bhi long video ka pinned comment lagana hai.

## Kaam ki list
1. Script likhna (Devanagari, ~110 lines), `longform/book-01-dont-believe/script.json` mein, `story_video.py` ke format mein.
2. **Pravin se script approve karwana.**
3. Sarvam voice: `python tools/story_video.py voice longform/book-01-dont-believe` (~Rs 50). Lambai check karni hai: 18–22 min.
4. ChatGPT se ~35–40 images (Chrome mein) → `img/NN.png`
5. `python tools/story_video.py build ...`, phir thumbnail banana aur captions.md likhna.
6. **Pravin se poochna**, phir push karna aur schedule karna (YT 20:00, uske baad FB, phir IG trailer).

## Agli 2 books (isi template par)
- Chinta: *Don't Believe Everything You Think* ke baad ek anxiety wali book (Book Peak par Unwinding Anxiety 10 lakh views laayi thi).
- Focus: *Essentialism* / focus wali book (reference video 35 lakh views).

## Update 26 Nov (Pravin)
- Doctor wali line hata di. Images par "no text / neutral rang / asli cover nahi" wale rule bhi hata diye (`"neutral": false`).
- **Book ka poster lagega:** asli cover `cover.jpg` (is folder mein). Ye 3 jagah lagega: (1) jahan book ka naam aata hai, wahan blur background par bada cover; (2) aakhir ke saar mein chhota cover; (3) thumbnail mein cover aur "सोचना बंद करो".
- **Text captions:** `"captions": true`. Har line neeche safed Hindi text mein, kaali patti par (`story_video.py` mein naya option). Kul ~517 caption lines bani.
