# Ekstraklasa K10 — Saturday recap (model vs market vs result)

Predicted before kickoff, committed to git with timestamps. Results added after. No fitting the model backwards.

## The three matches

| Match | Model | Market | Actual cards | My lean | Hit? |
|---|---|---|---|---|---|
| Cracovia – Zagłębie | 3.34 | ~3.7 | 5 | UNDER | no |
| Śląsk – Lech | 3.96 | ~3.5 | 6 | OVER | yes |
| Jagiellonia – Górnik | 3.30 | ~3.7 | 6 | UNDER | no |

All three went over the model. Leans: 1 of 3.

## The honest verdict

The tempting read is "the model runs too low, recalibrate." It's the wrong read — because the market missed low too (lines 3.5–3.7, actual 5–6). When model and market miss the same way, it isn't an edge I lost. It's a hot round.

The next morning I tested the obvious explanations against two seasons of data (599 matches):

- **post–international-break → more cards** → no effect (4.32 vs 4.42, t≈0.35)
- **rule change → step between seasons** → none (4.30 vs 4.38, t≈0.5)
- **coaches sub off booked players** → disappears once you control for position (z 2.3 → 0.26)

Three tidy hypotheses, three honest no's. The only signal that survives every test is the referee's baseline. Everything else is match noise — about ±1.5 cards a game.

---

## X post

Ekstraklasa K10 Saturday — predicted before kickoff, timestamped in git.

Cards: all 3 went over my model (5 · 6 · 6 vs 3.3–4.0). Leans: 1/3.

Honest bit: the market missed low too. Not a lost edge — a hot round.

mr73biio.github.io/ekstraklasa-k10-sat.html
#Ekstraklasa #footballanalytics

---

## LinkedIn

Last weekend I did the same thing I always do with my Ekstraklasa cards model: I wrote the predictions down before kickoff and committed them to git, so the timestamp proves the prediction came before the result. No fitting the model backwards.

Three Saturday matches. Here's how it went.

All three landed over my model — 5, 6 and 6 cards, against a model of 3.3 to 4.0. My leans scored 1 out of 3.

Easy story to tell: "the model runs too low, time to recalibrate." But that's the wrong story, and the data says so. The market missed low too — the lines sat at 3.5–3.7, and the matches delivered 5–6. When my model and the market both miss the same way, it isn't an edge I lost. It's a hot round.

So the next morning I tested the obvious explanations against two seasons of data:
– "the international break inflates cards" → no effect
– "rule changes pushed cards up" → no step between seasons
– "coaches sub off booked players to protect them" → disappears once you control for position

Three tidy hypotheses, three honest no's. The only signal that survives every test is the referee's baseline. Everything else is match noise — about ±1.5 cards a game.

That's the whole point of doing it in public, before the result: you find out what's real, not what's comfortable.

—
Marcin Ruszczak · PL · DE · RU · EN
mr73biio.github.io/ekstraklasa-k10-sat.html
