"""Conservative importer for the official Ekta Mandir event listing.

Unlike generic flyer OCR, the religious-events page has individually dated
event cards. Read day/month/weekday from each card and corroborate the year
against the official site calendar year. Never synthesize recurrence dates.
"""
from datetime import date, datetime, timedelta, time
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit

MONTHS = {name: i for i, name in enumerate(
    ("January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"), 1)}
MONTH_WORD = "|".join(MONTHS)
WEEKDAY_WORD = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
CARD_DATE = re.compile(
    rf"\b(0?[1-9]|[12]\d|3[01])\s+({MONTH_WORD})\s+"
    rf"(?:EktaMandir\s+)?({WEEKDAY_WORD})\b", re.I)
ANCHORED_YEAR = re.compile(r"\bEktaMandir\s+Event\s+Calendar\s+(20\d{2})\b", re.I)
# Monthly named ceremonies and special religious celebrations belong in this
# calendar. Routine classes, weekly chanting, and generic recurring listings do not.
SPECIAL = re.compile(
    r"balaji abishek|sundarakand|pradosham|abhishe[kc]|puja|pooja|"
    r"utsav|festival|navaratri|diwali|deepavali|kalyan|bhajan|mandala|"
    r"homam|rudram|shivaratri|janmashtami|ram navami|celebration", re.I)
ROUTINE = re.compile(
    r"recurring events|vidya peeth|classes|yoga|hanuman chalisa|"
    r"sahasranamam chanting|sunday mahaprasad", re.I)
DETAIL_DATE = re.compile(
    r"\bDate\s+([A-Za-z]{3})\s+(\d{1,2})\s+(20\d{2})\b", re.I)
DETAIL_TIME = re.compile(
    r"\bTime\s+(\d{1,2}):(\d{2})\s*(am|pm)\s*[-–]\s*"
    r"(\d{1,2}):(\d{2})\s*(am|pm)\b", re.I)
HOME_HEAD = re.compile(r"\b([A-Za-z]+)\s+(20\d{2})\s+Events\b", re.I)
HOME_EVENT = re.compile(
    r"\b(TatTva[nm]Asi)\s*[-–]\s*(\d{1,2})(?:st|nd|rd|th)?\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\b", re.I)
ADDRESS = "Bharatiya Ekta Mandir, 2804 W Maryland Ave, Phoenix, AZ 85017, USA"


class CardParser(HTMLParser):
    """Pair each h4 event title with the nearest preceding visible date card."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.context = []
        self.cards = []
        self.title_parts = None
        self.title_href = None
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.hidden += 1
        if self.hidden:
            return
        attrs = dict(attrs)
        if tag == "h4":
            self.title_parts = []
            self.title_href = None
        elif tag == "a" and self.title_parts is not None and attrs.get("href"):
            self.title_href = attrs["href"]

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.hidden = max(0, self.hidden - 1)
            return
        if tag == "h4" and self.title_parts is not None:
            title = " ".join("".join(self.title_parts).split())
            preceding = " ".join(self.context[-30:])
            matches = list(CARD_DATE.finditer(preceding))
            if title and matches:
                self.cards.append((title, matches[-1], self.title_href))
            self.title_parts = None
            self.title_href = None

    def handle_data(self, data):
        if self.hidden:
            return
        value = " ".join(data.split())
        if not value:
            return
        if self.title_parts is not None:
            self.title_parts.append(value)
        else:
            self.context.append(value)
            if len(self.context) > 150:
                self.context = self.context[-100:]


def text_only(html):
    class Visible(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.parts = []
            self.hidden = 0
        def handle_starttag(self, tag, attrs):
            if tag in ("style", "script", "noscript"):
                self.hidden += 1
        def handle_endtag(self, tag):
            if tag in ("style", "script", "noscript"):
                self.hidden = max(0, self.hidden - 1)
        def handle_data(self, data):
            if not self.hidden:
                self.parts.append(data)
    p = Visible()
    p.feed(html)
    return " ".join(" ".join(p.parts).split())


def eligible(title):
    return bool(SPECIAL.search(title) and not ROUTINE.search(title))


def dated_card(day, month, weekday, current, anchor_year):
    """Do not infer years without the site's explicit, relevant calendar year."""
    if abs(anchor_year - current.year) > 1:
        return None
    month_no = next((n for name, n in MONTHS.items()
                     if name.lower() == month.lower()), None)
    if not month_no:
        return None
    for year in (current.year, current.year + 1):
        # The next January is possible in a late-year calendar, but never
        # invent events many months beyond the explicit calendar heading.
        if year not in (anchor_year, anchor_year + 1):
            continue
        try:
            candidate = date(year, month_no, int(day))
        except ValueError:
            return None
        if (current.date() <= candidate <= current.date() + timedelta(days=180)
                and candidate.strftime("%A").lower() == weekday.lower()):
            return candidate
    return None


def _clock(hour, minute, meridian):
    h = int(hour) % 12 + (12 if meridian.lower() == "pm" else 0)
    return time(h, int(minute))


def detail_times(html, event_day):
    """Use a detail page time only when its displayed date matches the card."""
    text = text_only(html)
    d = DETAIL_DATE.search(text)
    t = DETAIL_TIME.search(text)
    if not (d and t):
        return None
    try:
        listed = datetime.strptime(" ".join(d.groups()), "%b %d %Y").date()
    except ValueError:
        return None
    if listed != event_day:
        return None
    start = _clock(*t.groups()[:3])
    end = _clock(*t.groups()[3:])
    if end <= start:
        return None
    return start, end


def auto_from_ekta(url, now, fetcher):
    """Return normalized event dictionaries; fetcher must return official HTML."""
    from projects.build_feeds import normalize
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/Phoenix")
    html = fetcher(url)
    cards = CardParser()
    cards.feed(html)
    if not cards.cards:
        raise ValueError("Ekta Mandir event cards not found: importer requires review")
    heading_years = {int(x) for x in ANCHORED_YEAR.findall(text_only(html))}
    anchors = [year for year in heading_years if abs(year - now.year) <= 1]
    if not anchors:
        raise ValueError("Ekta Mandir listing lacks a relevant official calendar year")
    results = []
    seen = set()
    details = {}
    for title, match, href in cards.cards:
        if not eligible(title):
            continue
        when = next((d for yr in sorted(anchors, reverse=True)
                     if (d := dated_card(*match.groups(), now, yr))), None)
        if not when or (title.casefold(), when) in seen:
            continue
        seen.add((title.casefold(), when))
        link = urljoin(url, href or "")
        if urlsplit(link).scheme != "https" or (urlsplit(link).hostname or "").removeprefix("www.") != "ektamandiraz.org":
            link = url
        times = None
        if link != url:
            if link not in details:
                try:
                    details[link] = fetcher(link)
                except Exception:
                    details[link] = ""
            times = detail_times(details[link], when)
        start_time, end_time = times or (time(8), time(9))
        note = ("Organizer's matching detail page confirms this ceremony time."
                if times else
                "8:00–9:00 AM is a calendar reminder window, NOT a confirmed ceremony time. "
                "Check the official event page before visiting.")
        start = datetime.combine(when, start_time, tz).isoformat()
        end = datetime.combine(when, end_time, tz).isoformat()
        results.append(normalize({
            "title": f"Ekta Mandir — {title}",
            "start": start, "end": end, "location": ADDRESS,
            "url": link, "source": url,
            "description": "Official religious-events listing; day/month/weekday checked against the temple's "
                           "explicit calendar year. " + note
        }))
    # A one-off, dated special event appears on the temple homepage rather than
    # in the religious-events directory. Require a same-year month heading.
    home_url = "https://www.ektamandiraz.org/"
    try:
        home = text_only(fetcher(home_url))
        headings = {(m.group(1).lower(), int(m.group(2))) for m in HOME_HEAD.finditer(home)}
        for match in HOME_EVENT.finditer(home):
            title, day, month = match.groups()
            if (month.lower(), now.year) not in headings:
                continue
            try:
                when = date(now.year, MONTHS[month.capitalize()], int(day))
            except (ValueError, KeyError):
                continue
            if not now.date() <= when <= now.date() + timedelta(days=60):
                continue
            results.append(normalize({
                "title": "Ekta Mandir — TatTvamAsi Ayyappa Bhajan and Puja",
                "start": datetime.combine(when, time(8), tz).isoformat(),
                "end": datetime.combine(when, time(9), tz).isoformat(),
                "location": ADDRESS, "url": home_url, "source": home_url,
                "description": "Official temple homepage announcement. 8:00–9:00 AM is a reminder window, NOT a verified event time."
            }))
    except Exception:
        # Religious-events listing remains independently authoritative.
        pass
    return results
