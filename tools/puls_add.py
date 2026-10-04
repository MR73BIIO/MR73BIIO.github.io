#!/usr/bin/env python3
"""Puls - dziennik uderzen serca (MR73BIIO).

Jedno zycie = przewidywanie zacommitowane przed uruchomieniem -> wynik -> OUTCOME
zacommitowany i wypchniety. Puls zapisuje sam fakt zachowania (data, plaszczyzna,
werdykt, pieczec), nie tresc pracy.

Komendy:
  dodaj        nowy wpis (prediction / life / milestone / pause), commit i push strony
  zaleglosci   poranna kontrola: co otwarte, co czeka na publikacje, rytm tygodnia
  opublikowano dopisz link publikacji do wpisu z plaszczyzny otwartej
  bramka       otworz plaszczyzne (po decyzji); odsloniecie wpisow komenda `odslon`
  odslon       dopisz fakt / link / wynik do wpisu z plaszczyzny juz otwartej
  sprawdz      sprawdz pieczecie wpisow wobec historii lokalnych repo

Zabezpieczenia (odmowa PRZED commitem):
  - life bez pliku OUTCOME (wyjatek tylko --wstecz z --outcome-commit),
  - plik przewidywania / OUTCOME niezacommitowany, zmieniony lub niewypchniety,
  - na plaszczyznie zapieczetowanej: pole fact, link, score lub dowolny URL,
  - w kazdym polu tekstowym: wzorce z tools/.puls_bramki.local (lokalny, poza gitem).

Tylko biblioteka standardowa, Python 3.8+.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON = os.path.join(ROOT, "puls.json")
GATES = os.path.join(ROOT, "tools", ".puls_bramki.local")
KINDS = ("prediction", "life", "milestone", "pause")
VERDICTS = ("CONFIRMED", "REFUTED", "NO DATA")
TEXT_FIELDS = ("question", "fact", "link", "score")


def die(msg):
    sys.exit("ODMOWA: " + msg)


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo] + list(args), capture_output=True)
    if check and r.returncode != 0:
        die("git %s w %s: %s" % (" ".join(args), repo, r.stderr.decode(errors="replace").strip()))
    return r


# ------------------------------------------------------------------ dane
def load():
    with open(JSON, encoding="utf-8") as f:
        doc = json.load(f)
    validate(doc)
    return doc


def save(doc):
    validate(doc)
    with open(JSON, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")


def validate(doc):
    seen = set()
    prev = None
    for e in doc["entries"]:
        n = e["n"]
        if n in seen:
            die("powtorzony numer wpisu %d" % n)
        seen.add(n)
        if prev is not None and n != prev + 1:
            die("dziura w numeracji przed wpisem %d" % n)
        prev = n
        if e["kind"] not in KINDS:
            die("wpis %d: nieznany rodzaj %s" % (n, e["kind"]))
        if e["plane"] not in doc["planes"]:
            die("wpis %d: nieznana plaszczyzna %s" % (n, e["plane"]))
        if e.get("follows") is not None and e["follows"] not in seen:
            die("wpis %d: follows wskazuje wpis, ktorego wczesniej nie ma" % n)
        if e["kind"] == "life" and e.get("verdict") not in VERDICTS:
            die("wpis %d: life bez werdyktu" % n)
        sealed = doc["planes"][e["plane"]]["gate"] != "open"
        if sealed and not e.get("public"):
            for k in ("fact", "link", "score"):
                if e.get(k):
                    die("wpis %d: pole %s na plaszczyznie zapieczetowanej" % (n, k))


def gate_patterns():
    if not os.path.exists(GATES):
        die("brak %s (jeden wzorzec regex na linie: nazwy zza bramki, "
            "prywatne repo). Bez niego skrypt nie zapisuje." % GATES)
    pats = []
    with open(GATES, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                pats.append(re.compile(line, re.I))
    return pats


def check_text(entry, sealed):
    pats = gate_patterns()
    for k in TEXT_FIELDS:
        v = entry.get(k) or ""
        for p in pats:
            if p.search(v):
                die("pole %s zawiera wzorzec zza bramki (%s)" % (k, p.pattern))
        if sealed and k == "question" and re.search(r"https?://|www\.", v):
            die("adres w pytaniu na plaszczyznie zapieczetowanej")
    if sealed:
        for k in ("fact", "link", "score"):
            if entry.get(k):
                die("plaszczyzna zapieczetowana: pole %s musi byc puste" % k)


# ------------------------------------------------------------------ pieczecie
def seal_file(repo, path):
    """SHA-256 pliku w HEAD; plik musi byc zacommitowany, czysty i wypchniety."""
    if git(repo, "ls-files", "--error-unmatch", path, check=False).returncode:
        die("%s nie jest w gicie (%s). Najpierw commit." % (path, repo))
    if git(repo, "diff", "--quiet", "HEAD", "--", path, check=False).returncode:
        die("%s ma niezacommitowane zmiany." % path)
    up = git(repo, "rev-list", "--count", "@{u}..HEAD", check=False)
    if up.returncode:
        die("%s: galaz bez upstream, nie wiem, czy wypchnieta." % repo)
    if int(up.stdout.decode().strip() or 0) > 0:
        die("%s: commity niewypchniete. Najpierw push (zgodnosc 3 maszyn)." % repo)
    blob = git(repo, "show", "HEAD:" + path).stdout
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def seal_commit(repo, ref):
    h = git(repo, "rev-parse", ref + "^{commit}").stdout.decode().strip()
    return "git:" + h


# ------------------------------------------------------------------ stan
def followers(doc):
    return {e["follows"] for e in doc["entries"] if e.get("follows") is not None}


def closed_preds(doc):
    return {e["closes"] for e in doc["entries"] if e.get("closes") is not None}


def status_of(doc, e):
    if e["kind"] == "prediction":
        return "closed" if e["n"] in closed_preds(doc) else "open"
    if e["kind"] == "life" and e["verdict"] == "REFUTED":
        if e["n"] in followers(doc) or e.get("resolution") == "pre":
            return "closed"
        return "open"
    return "closed"


def refresh(doc):
    for e in doc["entries"]:
        e["status"] = status_of(doc, e)


def commit_site(doc, e, push=True):
    msg = "puls #%d: %s %s" % (e["n"], e["kind"], doc["planes"][e["plane"]]["label"])
    git(ROOT, "add", "puls.json")
    git(ROOT, "commit", "-m", msg)
    if push:
        git(ROOT, "push")
    print("zapisano wpis #%d (%s)%s" % (e["n"], msg, "" if push else ", bez push"))


def now_iso():
    return dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


# ------------------------------------------------------------------ komendy
def cmd_dodaj(a):
    doc = load()
    plane = doc["planes"].get(a.plane) or die("nieznana plaszczyzna %s" % a.plane)
    sealed = plane["gate"] != "open"
    e = dict(n=(doc["entries"][-1]["n"] + 1) if doc["entries"] else 1,
             date=a.date or now_iso(), kind=a.kind, plane=a.plane,
             question=a.question or "", verdict=a.verdict, score=a.score,
             public=not sealed, fact=a.fact or "", link=a.link or "",
             sha_pred=None, sha_outcome=None, follows=a.follows,
             resolution=a.resolution, closes=None, status="closed", pub=[])
    check_text(e, sealed)

    if a.kind in ("prediction", "life"):
        if not a.repo:
            die("--repo wymagane dla %s" % a.kind)
        if not a.pred:
            die("--pred (plik przewidywania w repo) wymagane")
        e["sha_pred"] = seal_file(a.repo, a.pred)
    if a.kind == "prediction":
        if a.verdict or a.outcome:
            die("przewidywanie nie ma werdyktu ani OUTCOME")
        if any(x.get("sha_pred") == e["sha_pred"] for x in doc["entries"]):
            die("to przewidywanie juz jest w Pulsie")
    if a.kind == "life":
        if a.verdict not in VERDICTS:
            die("--verdict CONFIRMED | REFUTED | 'NO DATA'")
        if a.outcome:
            e["sha_outcome"] = seal_file(a.repo, a.outcome)
        elif a.outcome_commit and a.wstecz:
            e["sha_outcome"] = seal_commit(a.repo, a.outcome_commit)
        else:
            die("life bez pliku OUTCOME (--outcome). Zycie nie jest zamkniete.")
        for x in doc["entries"]:
            if x["kind"] == "prediction" and x.get("sha_pred") == e["sha_pred"]:
                e["closes"] = x["n"]
        if e["closes"] is None and not a.wstecz:
            print("uwaga: brak wpisu prediction z ta pieczecia (przewidywanie nie bylo w Pulsie przed wynikiem)")
    if a.kind == "milestone" and not (a.question and (a.link or sealed)):
        die("milestone: --question i --link")
    if a.kind == "pause":
        e["question"] = a.question or "przerwa"
        if a.fact or a.link:
            die("pauza: tylko powod ogolny w --question, bez szczegolow")
    if a.follows is not None and not any(x["n"] == a.follows for x in doc["entries"]):
        die("--follows %d: nie ma takiego wpisu" % a.follows)

    doc["entries"].append(e)
    refresh(doc)
    save(doc)
    commit_site(doc, e, push=not a.bez_push)


def week_bounds(d):
    start = (d - dt.timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + dt.timedelta(days=7)


def cmd_zaleglosci(a):
    doc = load()
    refresh(doc)
    E = doc["entries"]
    planes = doc["planes"]

    def show(title, rows):
        print("\n== %s (%d)" % (title, len(rows)))
        for e in rows:
            print("  #%-3d %s  %-7s %s  %s" % (e["n"], e["date"][:10], planes[e["plane"]]["label"],
                                             e.get("verdict") or e["kind"], e["question"][:70]))

    show("przewidywania bez wyniku", [e for e in E if e["kind"] == "prediction" and e["status"] == "open"])
    show("REFUTED bez diagnozy", [e for e in E if e["kind"] == "life" and e["status"] == "open"])
    show("zycia z plaszczyzn otwartych bez publikacji",
         [e for e in E if e["kind"] in ("life", "milestone") and planes[e["plane"]]["gate"] == "open" and not e.get("pub")])
    show("zapieczetowane, czekaja na bramke", [e for e in E if planes[e["plane"]]["gate"] != "open"])

    now = dt.datetime.now().astimezone()
    s, t = week_bounds(now)
    lives = [e for e in E if e["kind"] == "life" and s <= dt.datetime.fromisoformat(e["date"]) < t]
    need = doc["rhythm"]["min_lives_per_week"]
    print("\n== rytm tygodnia od %s: %d/%d zamknietych zyc%s" % (
        s.date(), len(lives), need, "" if len(lives) >= need else "  <- brakuje %d" % (need - len(lives))))


def find(doc, n):
    for e in doc["entries"]:
        if e["n"] == n:
            return e
    die("nie ma wpisu %d" % n)


def cmd_opublikowano(a):
    doc = load()
    e = find(doc, a.n)
    if doc["planes"][e["plane"]]["gate"] != "open":
        die("wpis %d jest za bramka, nie publikujemy" % a.n)
    for u in a.url:
        check_text({"link": u}, False)
        if u not in e["pub"]:
            e["pub"].append(u)
    save(doc)
    git(ROOT, "add", "puls.json")
    git(ROOT, "commit", "-m", "puls #%d: publikacja" % a.n)
    if not a.bez_push:
        git(ROOT, "push")
    print("wpis #%d: %d link(i) publikacji" % (a.n, len(e["pub"])))


def cmd_bramka(a):
    doc = load()
    p = doc["planes"].get(a.plane) or die("nieznana plaszczyzna")
    p["gate"] = "open"
    save(doc)
    git(ROOT, "add", "puls.json")
    git(ROOT, "commit", "-m", "puls: plaszczyzna %s otwarta" % p["label"])
    if not a.bez_push:
        git(ROOT, "push")
    print("plaszczyzna %s otwarta; wpisy odslaniaj komenda `odslon`" % p["label"])


def cmd_odslon(a):
    doc = load()
    e = find(doc, a.n)
    if doc["planes"][e["plane"]]["gate"] != "open":
        die("plaszczyzna nadal zapieczetowana (najpierw `bramka`)")
    new = dict(e, fact=a.fact or e["fact"], link=a.link or e["link"], score=a.score or e["score"],
               question=a.question or e["question"], public=True)
    check_text(new, False)
    e.update(new)
    save(doc)
    git(ROOT, "add", "puls.json")
    git(ROOT, "commit", "-m", "puls #%d: odsloniecie" % a.n)
    if not a.bez_push:
        git(ROOT, "push")
    print("wpis #%d odsloniety" % a.n)


def cmd_sprawdz(a):
    doc = load()
    blobs, commits = {}, set()
    for repo in a.repo:
        name = os.path.basename(os.path.abspath(repo))
        lst = git(repo, "cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype)").stdout.decode().split()
        ids = [lst[i] for i in range(0, len(lst), 2) if lst[i + 1] == "blob"]
        commits.update(lst[i] for i in range(0, len(lst), 2) if lst[i + 1] == "commit")
        r = subprocess.run(["git", "-C", repo, "cat-file", "--batch"], input=("\n".join(ids) + "\n").encode(),
                           capture_output=True)
        buf, pos = r.stdout, 0
        while pos < len(buf):
            nl = buf.index(b"\n", pos)
            size = int(buf[pos:nl].split()[2])
            data = buf[nl + 1:nl + 1 + size]
            pos = nl + 1 + size + 1
            blobs.setdefault(hashlib.sha256(data).hexdigest(), name)
    ok = miss = 0
    for e in doc["entries"]:
        for k in ("sha_pred", "sha_outcome"):
            v = e.get(k)
            if not v:
                continue
            kind, h = v.split(":", 1)
            hit = blobs.get(h) if kind == "sha256" else (h if h in commits else None)
            if hit:
                ok += 1
                print("  OK    #%-3d %-11s %s" % (e["n"], k, kind))
            else:
                miss += 1
                print("  BRAK  #%-3d %-11s %s %s" % (e["n"], k, kind, h[:16]))
    print("\nzgodne: %d, nieznalezione w podanych repo: %d" % (ok, miss))
    print("(BRAK = pieczec z repo, ktorego nie podano, albo niezgodnosc do wyjasnienia)")


def main():
    ap = argparse.ArgumentParser(description="Puls MR73BIIO")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("dodaj")
    d.add_argument("--kind", choices=KINDS, required=True)
    d.add_argument("--plane", required=True)
    d.add_argument("--question")
    d.add_argument("--repo")
    d.add_argument("--pred", help="sciezka pliku przewidywania w repo")
    d.add_argument("--outcome", help="sciezka pliku OUTCOME w repo")
    d.add_argument("--outcome-commit", help="tylko z --wstecz")
    d.add_argument("--verdict", choices=VERDICTS)
    d.add_argument("--score")
    d.add_argument("--fact")
    d.add_argument("--link")
    d.add_argument("--follows", type=int)
    d.add_argument("--resolution", choices=["pre"], help="REFUTED zamkniety konsekwencja zapisana przed wynikiem")
    d.add_argument("--date")
    d.add_argument("--wstecz", action="store_true")
    d.add_argument("--bez-push", action="store_true")
    d.set_defaults(f=cmd_dodaj)

    z = sub.add_parser("zaleglosci")
    z.set_defaults(f=cmd_zaleglosci)

    o = sub.add_parser("opublikowano")
    o.add_argument("n", type=int)
    o.add_argument("url", nargs="+")
    o.add_argument("--bez-push", action="store_true")
    o.set_defaults(f=cmd_opublikowano)

    b = sub.add_parser("bramka")
    b.add_argument("plane")
    b.add_argument("--bez-push", action="store_true")
    b.set_defaults(f=cmd_bramka)

    s = sub.add_parser("odslon")
    s.add_argument("n", type=int)
    s.add_argument("--fact")
    s.add_argument("--link")
    s.add_argument("--score")
    s.add_argument("--question")
    s.add_argument("--bez-push", action="store_true")
    s.set_defaults(f=cmd_odslon)

    c = sub.add_parser("sprawdz")
    c.add_argument("--repo", action="append", required=True)
    c.set_defaults(f=cmd_sprawdz)

    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
