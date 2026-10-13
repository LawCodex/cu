#!/usr/bin/env python3
"""Cuba: Gaceta Oficial de la República de Cuba (https://www.gacetaoficial.gob.cu).

1. search ("Búsqueda avanzada", POST /es/getdata) by type of norm: Constitución, Código de
   Comercio, Ley, Decreto-Ley  -> list of norm records
2. norm record pages (metadata: Gaceta edition, identifier GOC-..., summary, number, year,
   amending / repealing norms)
3. Gaceta edition pages -> PDF of the edition; each norm is cut out of the edition text using
   its GOC identifier (printed in the Gaceta above every norm).

robots.txt: Crawl-delay 10 -> one request every 10 s.
Usage: cu_fetch.py [search|records|gacetas|convert|all]
"""
import json
import os
import re
import sys
import time
import unicodedata
from datetime import date
from html import unescape

import requests
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cu_pdfmd as P  # noqa: E402

RAW = os.environ.get("RAW", "/Users/magicaltux/projects/lawcodex/_raw/cu")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
SITE = "https://www.gacetaoficial.gob.cu"
TODAY = date.today().isoformat()
TYPES = {"4777": "Constitución", "4330": "Código de Comercio", "11": "Ley", "12": "Decreto Ley"}
DELAY = 10.0
s = requests.Session()
s.headers["User-Agent"] = UA
_last = [0.0]


def req(method, url, **kw):
    for k in range(6):
        w = DELAY - (time.time() - _last[0])
        if w > 0:
            time.sleep(w)
        _last[0] = time.time()
        try:
            r = s.request(method, url, timeout=(30, 900), **kw)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
            print("HTTP", r.status_code, url, file=sys.stderr, flush=True)
        except requests.RequestException as e:
            print("ERR", url, e, file=sys.stderr, flush=True)
        time.sleep(30 * (k + 1))
    return None


def text(html):
    html = re.sub(r"<(script|style).*?</\1>", "", html, flags=re.S)
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html)))


def slug(t, n=80):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:n].rstrip("-")


def search():
    out = {}
    for code, name in TYPES.items():
        page = 1
        last = 1
        while page <= last:
            d = {"data[numero]": "", "data[anno]": "Cualquiera", "data[page]": str(page), "data[t_norma]": code,
                 "data[estado]": "Cualquiera", "data[organismo]": "Cualquiera", "data[identificador]": "",
                 "data[texto_norma]": "", "data[buscar]": "2"}
            r = req("POST", SITE + "/es/getdata", data=d, headers={"X-Requested-With": "XMLHttpRequest"})
            h = r.text if r else ""
            for path in re.findall(r'href="/?(?:es/)?([a-z0-9-]+-de-\d{4}-de-[a-z0-9-]+)"', h):
                out.setdefault(path, {"path": path, "tipo": name})
            pages = [int(x) for x in re.findall(r'data-page="(\d+)"', h)]
            last = max(pages + [page])
            page += 1
        print(name, sum(1 for v in out.values() if v["tipo"] == name), flush=True)
    json.dump(list(out.values()), open(os.path.join(RAW, "search.json"), "w"), ensure_ascii=False, indent=0)


def records():
    rows = json.load(open(os.path.join(RAW, "search.json")))
    d = os.path.join(RAW, "records")
    os.makedirs(d, exist_ok=True)
    for r in rows:
        p = os.path.join(d, r["path"] + ".html")
        if not os.path.exists(p):
            x = req("GET", f"{SITE}/es/{r['path']}")
            open(p, "w", encoding="utf-8").write(x.text if x else "")
        h = open(p, encoding="utf-8").read()
        t = text(h)
        def f(lab, nxt):
            m = re.search(re.escape(lab) + r"\s*(.*?)\s*(?:" + nxt + ")", t)
            return m.group(1).strip() if m else None
        nxt = r"Identificador de norma:|Resumen:|Número:|Año:|Palabras Claves:|Anotada y concordada:|Normas que modifica:|Normas que deroga:|Normas que la modifican:|Norma que la deroga:|www\.gacetaoficial"
        r["titulo"] = (re.search(r"<title>(.*?)\s*\|", h) or [None, None])[1]
        r["publicado_en"] = f("Publicado en:", nxt)
        r["identificador"] = f("Identificador de norma:", nxt)
        r["resumen"] = f("Resumen:", nxt)
        r["numero"] = f("Número:", nxt)
        r["anio"] = f("Año:", nxt)
        r["modifica"] = f("Normas que modifica:", nxt)
        r["deroga"] = f("Normas que deroga:", nxt)
        r["modificada_por"] = f("Normas que la modifican:", nxt)
        r["derogada_por"] = f("Norma que la deroga:", nxt)
        m = re.search(r'href="/es/(gaceta-oficial-[^"]+)"', h)
        r["gaceta_path"] = m.group(1) if m else None
    json.dump(rows, open(os.path.join(RAW, "records.json"), "w"), ensure_ascii=False, indent=0)
    print("records", len(rows), "with gaceta", sum(1 for r in rows if r["gaceta_path"]))


def gacetas():
    rows = json.load(open(os.path.join(RAW, "records.json")))
    d = os.path.join(RAW, "gacetas")
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(RAW, "tmp.pdf")
    for g in sorted({r["gaceta_path"] for r in rows if r.get("gaceta_path")}):
        out = os.path.join(d, g + ".json")
        if os.path.exists(out):
            continue
        x = req("GET", f"{SITE}/es/{g}")
        pdfs = re.findall(r'href="([^"]+\.pdf)"', x.text if x else "", re.I)
        res = {"page": f"{SITE}/es/{g}", "pdf": None, "pages": None}
        for u in pdfs[:1]:
            u = u if u.startswith("http") else SITE + ("" if u.startswith("/") else "/") + u
            res["pdf"] = u
            for k in range(3):
                y = req("GET", u)
                if not y:
                    break
                open(tmp, "wb").write(y.content)
                if P.pdf_ok(tmp):
                    res["pages"] = P.extract_pages(tmp)
                    break
        json.dump(res, open(out, "w"), ensure_ascii=False)
        if os.path.exists(tmp):
            os.remove(tmp)
        print("gaceta", g, "ok" if res["pages"] else "NO TEXT", flush=True)


def cut(pages, ident):
    """Text of the norm: from an occurrence of its GOC identifier to the next different GOC
    identifier. The identifier also appears in the issue's summary, so the longest such span wins."""
    full = "\n".join(pages)
    if not ident:
        return None
    pat = re.escape(ident).replace(r"\-", r"\s*-\s*")
    nxt = re.compile(r"GOC\s*-\s*\d{4}\s*-\s*\d+\s*-\s*[A-Z]+\d+")
    norm = re.sub(r"\s", "", ident)
    best = None
    for ms in re.finditer(pat, full):
        end = len(full)
        for m in nxt.finditer(full, ms.end()):
            if re.sub(r"\s", "", m.group(0)) != norm:
                end = m.start()
                break
        seg = full[ms.start():end]
        if best is None or len(seg) > len(best):
            best = seg
    return best


def _line_back(full, pos, n):
    """Position of the start of the n-th line before pos."""
    for _ in range(n + 1):
        pos = full.rfind("\n", 0, max(0, pos - 1))
        if pos < 0:
            return 0
    return pos + 1


def cut_by_heading(pages, tipo, num):
    """Fallback for norms without (found) GOC identifier: locate "LEY No. N" / "DECRETO-LEY No. N"
    and take from the issuer's "HAGO SABER" block before it to the next "HAGO SABER" block."""
    if not num:
        return None
    full = "\n".join(pages)
    word = r"DECRETO[- ]?LEY" if tipo == "Decreto Ley" else r"LEY"
    best = None
    for m in re.finditer(r"(?<![A-Z-])" + word + r"\s+(?:No\.|NO\.|N[ÚU]MERO|N[ÚU]M\.)\s*" + re.escape(str(num)) + r"\b", full):
        prev_dado = full.rfind("DADO", 0, m.start())
        hs = full.rfind("HAGO SABER", max(0, prev_dado), m.start())
        start = _line_back(full, hs, 2) if hs >= 0 else _line_back(full, m.start(), 0)
        nxt = full.find("HAGO SABER", m.end())
        end = _line_back(full, nxt, 2) if nxt >= 0 else len(full)
        seg = full[start:end]
        if "Artículo" not in seg and "ARTICULO" not in seg.upper():
            continue
        if best is None or len(seg) > len(best):
            best = seg
    return best


def convert():
    rows = json.load(open(os.path.join(RAW, "records.json")))
    st = {}
    for r in rows:
        g = r.get("gaceta_path")
        p = os.path.join(RAW, "gacetas", (g or "") + ".json")
        if not g or not os.path.exists(p):
            st["no_gaceta"] = st.get("no_gaceta", 0) + 1
            continue
        G = json.load(open(p))
        if not G.get("pages"):
            st["no_text"] = st.get("no_text", 0) + 1
            continue
        seg = cut(G["pages"], r.get("identificador"))
        if not seg or len(seg) < 200:
            seg = cut_by_heading(G["pages"], r["tipo"], r.get("numero"))
        if not seg or len(seg) < 200:
            st["not_found"] = st.get("not_found", 0) + 1
            continue
        lines = [l for l in seg.split("\n")]
        md = P.lines_to_md(P.clean_pages(["\n".join(lines)], head_n=0, foot_n=0))
        tipo = r["tipo"]
        folder = {"Constitución": "constitucion", "Código de Comercio": "codigos", "Ley": "leyes", "Decreto Ley": "decretos-leyes"}[tipo]
        anio = r.get("anio") or "s-f"
        num = r.get("numero") or "sn"
        title = (r.get("titulo") or f"{tipo} {num} de {anio}").strip()
        if r.get("resumen"):
            title_full = f"{title} — {r['resumen'].strip(' “”\".')}"
        else:
            title_full = title
        fn = f"{folder}/{slug(r['path'], 90)}.md"
        front = {"title": title_full, "identifier": r.get("identificador"), "type": {"Constitución": "constitution", "Código de Comercio": "code",
                 "Ley": "act", "Decreto Ley": "decree-law"}[tipo], "jurisdiction": "cu", "language": "es",
                 "year": int(anio) if str(anio).isdigit() else None, "gaceta_oficial": r.get("publicado_en"),
                 "status": "repealed" if (r.get("derogada_por") and "No existen" not in r["derogada_por"]) else "in_force",
                 "amended_by": r.get("modificada_por") if r.get("modificada_por") and "No existen" not in r["modificada_por"] else None,
                 "source": f"{SITE}/es/{r['path']}", "source_pdf": G.get("pdf"), "retrieved": TODAY}
        fm = yaml.safe_dump(front, allow_unicode=True, sort_keys=False, width=1000).strip()
        path = os.path.join(REPO, fn)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write("\n".join(["---", fm, "---", "", f"# {title_full}", "",
            f"> Texto publicado en la {r.get('publicado_en') or 'Gaceta Oficial'} (texto original, no consolidado).", "", md, ""]))
        st[folder] = st.get(folder, 0) + 1
    print(st)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    for step, fn in (("search", search), ("records", records), ("gacetas", gacetas), ("convert", convert)):
        if cmd in (step, "all"):
            fn()
