# Recording script — `mubashir-en-us` (US accent)

**Format:** WAV, 48 kHz, 16-bit, mono. Same mic, same room, same gain
for all takes. Quiet room, no echo, no clipping. One sentence per file
if possible, named `en-us_001.wav`, `en-us_002.wav`, … with a manifest
(`scripts/record/manifest-template.csv`).

**Amount:** 20 minutes clean speech. This file is ~1,300 words
(≈ 10 minutes at natural pace). **Read it twice** — take 1 as written,
take 2 with slightly different emphasis and pacing — to reach 20 minutes.
Record the actual duration in the manifest; do not guess it.

**Accent:** speak in a deliberate **American accent** throughout:
rhotic /r/ (car, park, better), "schedule" as SKED-jule,
"tomato" as toh-MAY-toh, "herb" with the h, "leisure" as LEE-zher.

## 0. Voice-quality baseline (sustained vowels — record FIRST, before §A)

**Why first, and why it cannot be skipped:** without a baseline you
cannot tell whether a clone sounds "breathy" because that is how you
sound, or because the model added noise — and you cannot tell a tense
clone from a modal one. A baseline recorded months later, in a
different room or a different session, is not the same voice. Record
it now, in this session, on this mic, at this gain. It takes about
two minutes and is extra to the 20-minute connected-speech target.

**What to record:** three vowels × three voice qualities × three
takes each = 27 takes, one vowel per file.

- Vowels — hold each 3–5 s, steady pitch, no vibrato, no sliding up
  or down:
  - /a/ — "ah", as in *father*
  - /i/ — "ee", as in *see*
  - /u/ — "oo", as in *food*
- Qualities:
  - **Modal** — your normal speaking voice.
  - **Breathy** — deliberate breathy voice: audible air escaping,
    soft, sigh-like. Do not whisper — whisper has no vocal-fold
    vibration, so it is not a breathy vowel.
  - **Creaky** — deliberate vocal fry: very low, irregular, crackly.
    Short bursts are fine; do not force it if it hurts.
- File names: `en-us_base_<vowel>_<style>_<take>.wav`, e.g.
  `en-us_base_a_modal_1.wav`.

**Per-take acoustic log** — measure every take with the same pipeline
that will later compare clone vs reference (Praat/Parselmouth, or the
benchmark acoustic-profile script when it exists). Record it in the
manifest; leave a field blank if the tool cannot measure it — never
guess a number.

| Take | Vowel | Style | Duration (s) | Mean F0 (Hz) | F0 SD (Hz) | Intensity (dB) | Jitter (%) | Shimmer (%) | HNR (dB) | H1*–H2* (dB) | Session time |
|---|---|---|---|---|---|---|---|---|---|---|---|
| e.g. `en-us_base_a_modal_1` | /a/ | modal | | | | | | | | | |

**Rules:** same mic, room and gain as the rest of the session; log
session time per take (F0 drifts down and breathiness/creak rise as
the voice tires); do **not** average breathy + modal takes — phonation
is part of identity, mixing them blurs it; use the modal /a, i, u/
means as the reference band for every later "too clean / too breathy"
judgement — compare clone vs this baseline, same text, same pipeline,
never against clinical sustained-vowel norms.

## A. Statements

1. Hello, thank you for speaking with me today.
2. The role is based in Manchester, about twelve miles from your postcode.
3. We offer free online tools with no signup and no hidden charges.
4. Your application has been received and is being reviewed.
5. The interview will last around thirty minutes.
6. Please bring a valid photo ID and your right to work documents.
7. Our office opens at nine in the morning and closes at five.
8. The training starts on Monday and runs for two full weeks.
9. You can download the file, edit it, and share it in seconds.
10. This calculator is completely free and works in your browser.

## B. Questions (rising intonation)

11. Would Tuesday at ten a m work for an interview?
12. Are you available to start work next Monday?
13. Do you have experience in care work or hospitality?
14. How far do you live from the city center?
15. Can you work weekends and night shifts if needed?
16. What is the best number to reach you on?
17. Have you worked in a warehouse before?
18. Would you like me to send the details by email?

## C. Numbers, money, dates, postcodes

19. One, two, three, four, five, six, seven, eight, nine, ten.
20. Eleven, twelve, twenty, thirty, forty, fifty, sixty, seventy, eighty, ninety, one hundred.
21. The pay is thirteen pounds fifty per hour.
22. The salary is twenty eight thousand dollars a year.
23. Your shift starts at seven thirty in the morning.
24. The meeting is on the twenty third of October, twenty twenty six.
25. Please call zero seven seven zero zero nine zero zero four six one.
26. The postcode is S W 1 A 1 A A, and the second one is M 1 1 A E.
27. The discount is twenty percent off the regular price.
28. The file is two hundred and fifty kilobytes, and it took three seconds to convert.

## D. Recruitment phrases (Xplogent)

29. Thank you for your time today, Sarah. I will pass your details to the hiring manager.
30. The client is looking for two care assistants for the night shift in Kingsbury.
31. The hourly rate is twelve pounds fifty, paid weekly on Friday.
32. You will need a D B S check before you can start.
33. The job is temporary to start, with a chance of going permanent.
34. Can you confirm your postcode so I can check the distance to the site?
35. The interview is at our Manchester office, about forty minutes by bus.
36. If you are interested, I can book you in for Thursday morning.

## E. Product phrases (xplosole)

37. Merge your PDFs for free, no signup, no watermark.
38. Remove the background from any photo in seconds.
39. Compress your images without losing quality.
40. This age calculator shows your exact age in years, months, and days.
41. Try more than two hundred and fifty free tools on xplosole dot com.

## F. Accent minimal set (use each word in a sentence)

42. I parked the car near the park after driving past the bath shop.
43. We will dance on Saturday, and I will check the schedule on Sunday.
44. I like tomato soup, but I never put herb in it.
45. Please bring water, and do it better than last time.
46. What about the laugh we heard near the grass by the clerk's office?
47. The vase is on the table, and we have leisure time this afternoon.

## G. Conversational / natural range (read naturally — NOT acted drama)

A monotone clean read produces a monotone clone. Vary your pace and
emphasis the way you would on a real call: pause where you would
pause, stress the word that matters, let questions rise. Do not
over-enunciate and do not perform — this is your normal speaking
voice in four everyday modes.

51. Neutral: Right, let's get started. I'll walk you through it step by step, and you can stop me any time.
52. Warm: That's great news, honestly. I'm really pleased for you — you've worked hard for this.
53. Firm: I understand, but the deadline is Friday, and I need the documents before then.
54. Questioning: So — what did you think of the role? Was there anything that didn't sound right?

## H. Long-form passage (2+ minutes — read in ONE take, do not stop)

Read this in one continuous take, at your normal speaking pace, with
natural pauses. Do not re-record a sentence if you stumble — keep
going, the way you would on a live call. This passage is the
long-form drift test: the clone must still sound like you at the end
of two minutes, not just at the start.

55. Let me tell you how a normal day goes, because it's never quite what people expect. I usually get up around six thirty, make coffee, and check my messages before the house wakes up. There's always something waiting — a candidate asking about a shift, a manager asking for an update, a file that needs converting before nine. I deal with the quick ones first, then I sit down properly and work through the rest. Around ten, the calls start. Some are short, just confirming a time or a postcode. Some are longer, and those are the ones I enjoy most, because that's when you actually get to know someone — what they've done, what they're good at, what kind of work they really want. I take notes as I go, because I never trust myself to remember the details later. By lunchtime I've usually spoken to six or seven people, and there's a list on my desk of who needs what. The afternoon is for follow-ups: sending details by email, booking interviews, chasing the one document that's always missing. It's not glamorous work, but it matters, and when someone calls back a week later to say they got the job, that's the whole point. That's why I do it. And honestly, the best calls are the ones where the person on the other end relaxes halfway through — you can hear it in their voice, the moment they stop reading from a script and start talking like themselves. That's when you know you've got the right person for the role.

## I. Long paragraphs (read slowly, natural pauses)

56. Good morning, and welcome to today's session. We are going to talk about how to prepare for your interview, what to bring, how to answer the most common questions, and what happens after the interview is over. If you have any questions at any point, please stop me and ask. There is no such thing as a silly question when it comes to your career, and I would much rather you ask now than worry about it later tonight.
57. Our website offers more than two hundred and fifty free tools for everyday work. You can merge PDF files, convert images, compress large files, and calculate your age, your salary, and your loan payments, all without creating an account. Everything runs in your browser, which means your files never leave your computer, and there is nothing to install. It is free today, and it will stay free.
58. The recruitment process has three steps. First, we have a short phone call to check your experience and your availability. Second, we invite you to an interview with the hiring manager, either in person or by video call. Third, if you are successful, we complete your checks and agree on a start date. The whole process usually takes about one week, and we will keep you updated at every stage.

## J. Systematic prosody (one page — record in the same session, after §G)

§G is natural conversational range; this block is controlled coverage
of the prosody the clone must reproduce — same sentence, different
structures, rates, breath groups and scenarios. About 3–4 minutes,
extra to the 20-minute target. Log mean F0, F0 SD, duration and
intensity per take in the manifest where the item asks for it.

59. Statements — falling contour, final lengthening.
    "The interview is on Thursday morning." / "Your application has
    been approved."
60. Yes/no questions — rising contour.
    "Are you free on Thursday morning?" / "Did you receive the email
    I sent yesterday?"
61. Wh-questions — falling contour, not rising.
    "What time does the interview start?" / "Where is the Manchester
    office?"
62. Lists — rise on each non-final item, fall on the last.
    "We need your photo ID, your postcode, and your right to work
    documents." / "You can merge PDFs, compress images, and calculate
    your age — all for free."
63. Contrastive focus — same sentence, three takes, stress a different
    word each time; keep everything else the same.
    Sentence: "The interview is on Thursday, not Friday."
    Take 1: stress INTERVIEW. Take 2: stress THURSDAY. Take 3: stress
    FRIDAY.
64. Long vs short — same idea, two lengths.
    Short: "The job is yours."
    Long: "The job is yours, and the hiring manager would like you to
    start on Monday morning, if that works for you."
65. Same sentence at three rates — "Please bring a valid photo ID and
    your right to work documents."
    Take 1: ~120 wpm (deliberate, slow). Take 2: ~150 wpm (normal
    conversation). Take 3: ~180 wpm (brisk, fast). Time each take and
    log the actual wpm in the manifest; do not guess it.
66. Breath-group variation — same sentence, two takes.
    "If you are interested, I can book you in for Thursday morning."
    Take 1: one breath group, no pause. Take 2: two breath groups —
    pause at the comma, breathe, then continue.
67. Emotion by scenario — play the situation, do not imitate an
    emotion. 2–3 takes per scenario; keep the take whose measured
    values match the target band (log mean F0, F0 SD, duration and
    intensity per take). Targets are relative to YOUR neutral, not
    absolute Hz values.
    - Warm — you are reassuring a worried candidate: "That's great
      news, honestly. I'm really pleased for you."
      Targets: slower rate, lower intensity, longer pauses, mean F0
      at or slightly below neutral, breathy/lax voice.
    - Firm — you are holding a deadline with someone who is late:
      "I understand, but the deadline is Friday, and I need the
      documents before then."
      Targets: raised, steady intensity; tense/pressed voice; short
      pauses; mean F0 moderately raised; precise articulation.
      Controlled firmness — not hot anger.
    - Excited — you are telling a candidate they got the job: "You
      got the job — congratulations, I'm delighted for you."
      Targets: mean F0 much higher, widest F0 range/SD, faster rate,
      higher intensity, few/short pauses.
