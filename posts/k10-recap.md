# Ekstraklasa Matchday 10 — recap

Closed: 2026-10-12 · 9/9 matches in the database · Marcin Ruszczak (MR73BIIO)

## The numbers (from the database, not from memory)

| Match | Referee | Cards model | Cards actual | Fouls |
|---|---|---:|---:|---:|
| Wieczysta – Wisła Płock | Frankowski | 3.50 | 4 | 21 |
| Raków – GKS Katowice | Kos | 4.26 | 5 | 24 |
| Cracovia – Zagłębie | Marciniak | 3.34 | 5 | 28 |
| Śląsk – Lech | Gryckiewicz | 3.96 | 6 | 24 |
| Jagiellonia – Górnik | Myć | 3.30 | 6 | 31 |
| Piast – Widzew | Przybył | 3.82 | 4 | 28 |
| Pogoń – Korona | Lasyk | 3.05 | 2 | 27 |
| Legia – Wisła Kraków | Sylwestrzak | 3.80 | 5 | 32 |
| Radomiak – Motor | Kwiatkowski | 3.47 | 7 | 30 |
| **Total** | | **32.5** | **44** | **245** |

- Cards: model 3.61 per match, actual 4.89. Over the model in 8 of 9.
- Fouls: 27.2 per match against a league average of about 25.5.
- Cards = yellow cards to players only. Cards to coaching staff are excluded (2 this round: Pogoń, Raków).

## What happened in the code

1. The source site changed in the middle of the round. Match tabs moved from sub-pages (`/statystyki/`, `/sklady/`) to anchors (`#statystyki`, `#sklady`). The old addresses redirected to the main page, so the scrapers saw only possession and shots.
2. The guards worked. Every run that missed cards or fouls printed "NOT saving" and wrote nothing. No bad data got in.
3. A diagnostic script showed what the bot actually sees. It was not bot blocking: both a headless and a normal browser profile got the same page. The fix: open the anchor directly, fall back to a JavaScript click (a page overlay was blocking mouse clicks).
4. Two new rules are now in code, not in my head:
   - a match is written only after the final whistle ("Koniec" on the page). I learned this one the hard way: a match was written at minute 64 and had to be removed;
   - a staff card (no player ID) never counts as a player card.
5. One script now runs the whole round (`kolejka.sh rozlicz`) and one shows what is in the database and what is missing (`kolejka.sh stan`).

## Statistics, honestly

The model aims at the season average, and the season average so far was low (3.66 cards per match). Matchday 10 ran hot: 4.89. One round is not enough to change the model. If Matchday 11 is again around 4.5 on normal scorelines, the referee baseline gets recalibrated. That decision is written down now, before Matchday 11 is played.
