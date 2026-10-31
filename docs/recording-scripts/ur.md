# Recording script — `mubashir-ur` (Urdu)

> **⚠️ Diacritics rule (standing — read before recording anything in
> this file):** every Urdu line in this script must be recorded from
> fully vocalised (اعراب والی) text — zabar َ, zer ِ, pesh ُ, shadd ّ
> and jazm ْ wherever they change the reading — plus its Roman/IPA
> gloss. Urdu Nastaliq normally omits most vowel diacritics, and the
> same consonant skeleton can be read several ways (homographs); the
> reader has to supply the missing vowels from context. PronouncUR,
> the standard Urdu G2P system, is only ~64% accurate on
> undiacritised text, so an undiacritised line is an ambiguous line.
> **Never record from undiacritised Nastaliq alone.** Before
> recording, check every line: add the diacritics, confirm the
> intended reading of any homograph in context, and read the Roman
> gloss aloud as a cross-check. The lines in §0 and §G below are
> printed fully vocalised; the lines in §§A–F are not yet vocalised
> — vocalise them, and verify each homograph, before recording them.
> A mispronunciation that comes from an ambiguous line is a text
> problem, not a model problem — do not blame the model for it.

**Format:** WAV, 48 kHz, 16-bit, mono. Same mic, same room, same gain
for all takes. Quiet room, no echo, no clipping. One sentence per file
if possible, named `ur_001.wav`, `ur_002.wav`, … with a manifest
(`scripts/record/manifest-template.csv`).

**Amount:** 20 minutes clean speech. This file is ~1,100 words
(≈ 10 minutes at natural pace). **Read it twice** — take 1 as written,
take 2 with slightly different emphasis and pacing — to reach 20 minutes.
Record the actual duration in the manifest; do not guess it.

**Status note:** Urdu is a gated spike (docs/URDU-SPIKE.md). Record
this set only after the owner confirms the spike is going ahead — the
recordings are still useful for the spike test (a 60-second proxy clip
unblocks testing) and for a future fine-tune.

**Script vs Roman Urdu:** each Urdu sentence is followed by its Roman
Urdu parallel in brackets, so the same content can test both inputs.
English loanwords (interview, CV, job, email) are written in Latin
letters inside the Urdu script and must be pronounced in English.

## 0. صوتی معیار کی بنیاد / Voice-quality baseline (sustained vowels — record FIRST, before §A)

**Why first, and why it cannot be skipped:** without a baseline you
cannot tell whether a clone sounds "breathy" because that is how you
sound, or because the model added noise — and you cannot tell a tense
clone from a modal one. A baseline recorded months later, in a
different room or a different session, is not the same voice. Record
it now, in this session, on this mic, at this gain. It takes about
two minutes and is extra to the 20-minute connected-speech target.

**What to record:** three vowels × three voice qualities × three
takes each = 27 takes, one vowel per file. (Diacritics rule above
applies here too — the vowel labels below are printed vocalised.)

- Vowels — hold each 3–5 s, steady pitch, no vibrato, no sliding up
  or down. These are Urdu's long vowels; keep them oral
  (non-nasalised) — vowel nasalisation is phonemic in Urdu, so a
  nasalised take is a different vowel:
  - /aː/ — آ (ā, as in آب "water")
  - /iː/ — اِی (ī, as in "see")
  - /uː/ — اُو (ū, as in "food")
- Qualities:
  - **Modal** — عام آواز, your normal speaking voice.
  - **Breathy** — سانس بھری آواز, deliberate breathy voice: audible
    air escaping, soft, sigh-like. Do not whisper — whisper has no
    vocal-fold vibration, so it is not a breathy vowel.
  - **Creaky** — کریکھی آواز (vocal fry), very low, irregular,
    crackly. Short bursts are fine; do not force it if it hurts.
- File names: `ur_base_<vowel>_<style>_<take>.wav`, e.g.
  `ur_base_a_modal_1.wav`.

**Per-take acoustic log** — measure every take with the same pipeline
that will later compare clone vs reference (Praat/Parselmouth, or the
benchmark acoustic-profile script when it exists). Record it in the
manifest; leave a field blank if the tool cannot measure it — never
guess a number.

| Take | Vowel | Style | Duration (s) | Mean F0 (Hz) | F0 SD (Hz) | Intensity (dB) | Jitter (%) | Shimmer (%) | HNR (dB) | H1*–H2* (dB) | Session time |
|---|---|---|---|---|---|---|---|---|---|---|---|
| e.g. `ur_base_a_modal_1` | /aː/ | modal | | | | | | | | | |

**Rules:** same mic, room and gain as the rest of the session; log
session time per take (F0 drifts down and breathiness/creak rise as
the voice tires); do **not** average breathy + modal takes — phonation
is part of identity, mixing them blurs it; use the modal /aː, iː, uː/
means as the reference band for every later "too clean / too breathy"
judgement — compare clone vs this baseline, same text, same pipeline,
never against clinical sustained-vowel norms.

## A. عام جملے (Everyday statements)

1. السلام علیکم، آپ سے بات کر کے خوشی ہوئی۔
   (Assalam o alaikum, aap se baat kar ke khushi hui.)
2. آپ کی درخواست موصول ہو گئی ہے اور اس کا جائزہ لیا جا رہا ہے۔
   (Aap ki darkhwast moosool ho gayi hai aur is ka jaiza liya ja raha hai.)
3. انٹرویو تقریباً تیس منٹ تک جاری رہے گا۔
   (Interview taqreeban tees minute tak jaari rahe ga.)
4. براہ کرم اپنا شناختی کارڈ اور ضروری دستاویزات ساتھ لائیں۔
   (Barah e karam apna shanakhti card aur zaroori dastawezaat saath laayen.)
5. ہمارا دفتر صبح نو بجے کھلتا ہے اور شام پانچ بجے بند ہوتا ہے۔
   (Hamara daftar subah nau bajay khulta hai aur shaam paanch bajay band hota hai.)
6. تربیت پیر سے شروع ہوگی اور دو ہفتے تک جاری رہے گی۔
   (Tarbiyat peer se shuru hogi aur do haftay tak jaari rahe gi.)
7. یہ کیلکولیٹر بالکل مفت ہے اور آپ کے براؤزر میں کام کرتا ہے۔
   (Yeh calculator bilkul muft hai aur aap ke browser mein kaam karta hai.)
8. آپ فائل ڈاؤن لوڈ کر سکتے ہیں، اس میں ترمیم کر سکتے ہیں اور سیکنڈوں میں شیئر کر سکتے ہیں۔
   (Aap file download kar saktay hain, is mein tarmeem kar saktay hain aur secondon mein share kar saktay hain.)

## B. سوالات (Questions)

9. کیا منگل کو صبح دس بجے انٹرویو کے لیے وقت مناسب ہے؟
   (Kya mangal ko subah das bajay interview ke liye waqt munasib hai?)
10. کیا آپ اگلے پیر سے کام شروع کر سکتے ہیں؟
    (Kya aap aglay peer se kaam shuru kar saktay hain?)
11. آپ سے رابطہ کرنے کے لیے بہترین نمبر کون سا ہے؟
    (Aap se raabta karnay ke liye behtareen number kaun sa hai?)
12. کیا آپ کو اس کام کا تجربہ ہے؟
    (Kya aap ko is kaam ka tajurba hai?)
13. کیا آپ ہفتے کے آخر میں کام کر سکتے ہیں؟
    (Kya aap haftay ke aakhir mein kaam kar saktay hain?)

## C. اعداد، رقم، تاریخیں (Numbers, money, dates)

14. ایک، دو، تین، چار، پانچ، چھ، سات، آٹھ، نو، دس۔
    (Aik, do, teen, chaar, paanch, chhay, saat, aath, nau, das.)
15. گیارہ، بارہ، بیس، تیس، چالیس، پچاس، ساٹھ، ستر، اسی، نوے، سو۔
    (Gyarah, barah, bees, tees, chalees, pachaas, saath, sattar, assi, nawway, sau.)
16. تنخواہ پچاس ہزار روپے ماہانہ ہے۔
    (Tankhwah pachaas hazaar rupay mahana hai.)
17. اس کی قیمت پانچ ہزار روپے ہے۔
    (Is ki qeemat paanch hazaar rupay hai.)
18. میٹنگ تئیس اکتوبر، دو ہزار چھبیس کو ہے۔
    (Meeting tayees October, do hazaar chhabbees ko hai.)
19. براہ کرم صفر تین سو بارہ، نو آٹھ سات چھ پانچ چار تین پر کال کریں۔
    (Barah e karam 0312-9876543 par call karen.)
20. چھوٹ بیس فیصد ہے۔
    (Chhoot bees feesad hai.)

## D. ملازمت سے متعلق جملے (Job phrases)

21. آپ کی CV موصول ہو گئی ہے، شکریہ۔
    (Aap ki CV moosool ho gayi hai, shukriya.)
22. یہ job لاہور میں ہے اور تنخواہ ہفتہ وار ادا کی جاتی ہے۔
    (Yeh job Lahore mein hai aur tankhwah hafta waar ada ki jati hai.)
23. انٹرویو کے بعد ہم آپ کو email کے ذریعے آگاہ کریں گے۔
    (Interview ke baad hum aap ko email ke zariye aagah karen ge.)
24. اگر آپ دلچسپی رکھتے ہیں تو میں آپ کا انٹرویو جمعرات کی صبح طے کر سکتا ہوں۔
    (Agar aap dilchaspi rakhtay hain to mein aap ka interview jumeraat ki subah tay kar sakta hoon.)

## E. قدرتی لہجہ / Conversational range (natural, not acted drama)

**نوٹ:** ایک ہی لہجے میں صاف پڑھنے سے clone بھی ایک ہی لہجے میں بولے گا۔
قدرتی انداز میں پڑھیں — جہاں آپ رکتے ہیں وہاں رکیں، سوال کو سوال کی طرح
پڑھیں، زور اس لفظ پر دیں جو اہم ہے۔ زیادہ صاف بولنے کی کوشش نہ کریں۔

27. Neutral: ٹھیک ہے، شروع کرتے ہیں۔ میں آپ کو مرحلہ وار بتاتا ہوں، اور آپ کسی بھی وقت مجھے روک سکتے ہیں۔
    (Theek hai, shuru kartay hain. Mein aap ko marhala waar batata hoon, aur aap kisi bhi waqt mujhe rok saktay hain.)
28. Warm: یہ بہت اچھی خبر ہے، واقعی۔ مجھے آپ کے لیے بہت خوشی ہوئی — آپ نے اس کے لیے بہت محنت کی ہے۔
    (Yeh bohat achhi khabar hai, waqai. Mujhe aap ke liye bohat khushi hui — aap ne is ke liye bohat mehnat ki hai.)
29. Firm: میں سمجھتا ہوں، لیکن آخری تاریخ جمعہ ہے، اور مجھے اس سے پہلے دستاویزات چاہییں۔
    (Mein samajhta hoon, lekin aakhri tareekh jumma hai, aur mujhe is se pehlay dastawezaat chahiye.)
30. Questioning: تو — آپ کو یہ کام کیسا لگا؟ کیا کوئی ایسی بات تھی جو ٹھیک نہ لگی ہو؟
    (To — aap ko yeh kaam kaisa laga? Kya koi aisi baat thi jo theek na lagi ho?)

**Long-form (2+ minutes, one take):** section F, items 31–32, read back
to back in ONE continuous take without stopping — this is the
long-form drift test (the clone must still sound like you at the end
of two minutes, not just at the start).

## F. طویل پیراگراف (Long paragraphs)

31. السلام علیکم اور آج کے سیشن میں خوش آمدید۔ آج ہم انٹرویو کی تیاری کے بارے میں بات کریں گے، آپ کو کیا ساتھ لانا چاہیے، عام سوالات کے جوابات کیسے دینے ہیں، اور انٹرویو کے بعد کیا ہوتا ہے۔ اگر کسی بھی وقت آپ کے ذہن میں کوئی سوال آئے تو براہ کرم مجھے روک کر پوچھیں۔ آپ کے کیریئر کے بارے میں کوئی سوال چھوٹا نہیں ہوتا، اور میں چاہتا ہوں کہ آپ ابھی پوچھیں بجائے اس کے کہ رات کو پریشان رہیں۔
32. ہماری ویب سائٹ روزمرہ کے کام کے لیے دو سو پچاس سے زیادہ مفت tools پیش کرتی ہے۔ آپ PDF فائلیں merge کر سکتے ہیں، تصاویر convert کر سکتے ہیں، بڑی فائلیں compress کر سکتے ہیں، اور اپنی عمر، تنخواہ اور قرض کی قسط کا حساب لگا سکتے ہیں، وہ بھی بغیر کوئی account بنائے۔ سب کچھ آپ کے براؤزر میں چلتا ہے، جس کا مطلب ہے کہ آپ کی فائلیں آپ کے کمپیوٹر سے باہر نہیں جاتیں، اور کچھ install کرنے کی ضرورت نہیں۔ یہ آج مفت ہے اور مفت ہی رہے گا۔

## G. منظم لہجہ / Systematic prosody (one page — record in the same session, after §E)

§E is natural conversational range; this block is controlled coverage
of the prosody the clone must reproduce — same sentence, different
structures, rates, breath groups and scenarios. About 3–4 minutes,
extra to the 20-minute target. Every line below is printed with full
diacritics + Roman gloss, per the diacritics rule at the top of this
file. Log mean F0, F0 SD, duration and intensity per take in the
manifest where the item asks for it.

33. Statements — falling contour, final lengthening (گرتا ہوا لہجہ).
    آپ کی دَرخواست مَنظُور ہو گئی ہے۔
    (Aap ki darkhwast manzoor ho gayi hai.)
    مُلاقات جُمعرات کی صُبح ہے۔
    (Mulaqat jumeraat ki subah hai.)
34. Yes/no questions — rising contour (سوال، اُٹھتا ہوا لہجہ).
    کیا آپ جُمعرات کی صُبح فارِغ ہیں؟
    (Kya aap jumeraat ki subah farigh hain?)
35. Wh-questions — falling contour, not rising.
    مُلاقات کِس وَقت شُروع ہوتی ہے؟
    (Mulaqat kis waqt shuru hoti hai?)
    دَفتر کہاں ہے؟
    (Daftar kahan hai?)
36. Lists — rise on each non-final item, fall on the last.
    ہمیں آپ کا شَناختی کارڈ، پوسٹ کوڈ اور ضَرُوری دَستاویزات چاہییں۔
    (Hamein aap ka shanakhti card, postcode aur zaroori dastawezaat chahiye.)
37. Contrastive focus — same sentence, three takes, stress a different
    word each time; keep everything else the same.
    Sentence: مُلاقات جُمعرات کو ہے، جُمعہ کو نہیں۔
    (Mulaqat jumeraat ko hai, jumma ko nahin.)
    Take 1: stress مُلاقات. Take 2: stress جُمعرات. Take 3: stress جُمعہ.
38. Long vs short — same idea, two lengths.
    Short: یہ نَوکری آپ کی ہے۔
    (Yeh naukri aap ki hai.)
    Long: یہ نَوکری آپ کی ہے، اور مینیجر چاہتے ہیں کہ آپ پیر کی صُبح سے کام شُروع کر دیں، اگر آپ کو مُناسِب ہو۔
    (Yeh naukri aap ki hai, aur manager chahtay hain ke aap peer ki subah se kaam shuru kar dein, agar aap ko munasib ho.)
39. Same sentence at three rates — بَراہِ کَرم اپنا شَناختی کارڈ اور ضَرُوری دَستاویزات ساتھ لائیں۔
    (Barah e karam apna shanakhti card aur zaroori dastawezaat saath laayen.)
    Take 1: ~120 wpm (deliberate, slow). Take 2: ~150 wpm (normal
    conversation). Take 3: ~180 wpm (brisk, fast). Time each take and
    log the actual wpm in the manifest; do not guess it.
40. Breath-group variation — same sentence, two takes.
    اَگر آپ دِلچَسپی رَکھتے ہیں تو میں آپ کا اِنٹرویو جُمعرات کی صُبح طے کر سَکتا ہوں۔
    (Agar aap dilchaspi rakhtay hain to mein aap ka interview jumeraat ki subah tay kar sakta hoon.)
    Take 1: one breath group, no pause. Take 2: two breath groups —
    pause after "ہیں تو", breathe, then continue.
41. Emotion by scenario — play the situation, do not imitate an
    emotion. 2–3 takes per scenario; keep the take whose measured
    values match the target band (log mean F0, F0 SD, duration and
    intensity per take). Targets are relative to YOUR neutral, not
    absolute Hz values.
    - Warm — you are reassuring a worried candidate:
      یہ بَہُت اَچھی خَبَر ہے، واقِعی۔ مُجھے آپ کے لیے بَہُت خُوشی ہُوئی۔
      (Yeh bohat achhi khabar hai, waqai. Mujhe aap ke liye bohat khushi hui.)
      Targets: slower rate, lower intensity, longer pauses, mean F0
      at or slightly below neutral, breathy/lax voice.
    - Firm — you are holding a deadline with someone who is late:
      میں سَمَجھتا ہوں، لیکِن آخِری تاریخ جُمعہ ہے، اور مُجھے اِس سے پَہلے دَستاویزات چاہییں۔
      (Mein samajhta hoon, lekin aakhri tareekh jumma hai, aur mujhe is se pehlay dastawezaat chahiye.)
      Targets: raised, steady intensity; tense/pressed voice; short
      pauses; mean F0 moderately raised; precise articulation.
      Controlled firmness — not hot anger.
    - Excited — you are telling a candidate they got the job:
      آپ کو نَوکری مِل گئی ہے — مُبارَک ہو، مُجھے آپ کے لیے بَہُت خُوشی ہے۔
      (Aap ko naukri mil gayi hai — mubarak ho, mujhe aap ke liye bohat khushi hai.)
      Targets: mean F0 much higher, widest F0 range/SD, faster rate,
      higher intensity, few/short pauses.
