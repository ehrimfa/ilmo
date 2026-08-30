#!/usr/bin/env python3
"""기념일(D-day) 계산기.

정본 데이터는 data/ddays.yaml 하나뿐이고, D-day 숫자와 캘린더 파일은 전부 여기서 계산한다.
음력 항목은 korean_lunar_calendar 로 매년 양력 날짜를 다시 구한다.

사용법:
    python3 scripts/dday.py list                 # 전체 목록 (앱 화면과 같은 순서)
    python3 scripts/dday.py list --within 60     # 60일 안에 오는 것만
    python3 scripts/dday.py list --group ours    # 그룹별
    python3 scripts/dday.py check                # 데이터 검증
    python3 scripts/dday.py ics --years 10       # dist/ddays.ics 생성
"""

import argparse
import datetime as dt
import sys
from pathlib import Path

import yaml
from korean_lunar_calendar import KoreanLunarCalendar

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "ddays.yaml"
WEEKDAYS = "월화수목금토일"


def load():
    with DATA.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def lunar_to_solar(lunar_year, month, day, leap=False):
    """음력 → 양력. 해당 음력 날짜가 그 해에 없으면 None."""
    cal = KoreanLunarCalendar()
    if not cal.setLunarDate(lunar_year, month, day, leap):
        return None
    iso = cal.SolarIsoFormat()
    if not iso:
        return None
    return dt.date.fromisoformat(iso)


def occurrences(entry, start_year, years):
    """start_year 부터 years 년치 양력 발생일을 순서대로 돌려준다."""
    out = []
    if entry["calendar"] == "solar":
        origin = entry["date"]
        for y in range(start_year, start_year + years):
            try:
                out.append(dt.date(y, origin.month, origin.day))
            except ValueError:  # 2월 29일 → 평년에는 2월 28일로
                out.append(dt.date(y, 2, 28))
    else:
        for y in range(start_year - 1, start_year + years + 1):
            d = lunar_to_solar(y, entry["lunar_month"], entry["lunar_day"],
                               entry.get("lunar_leap", False))
            if d is not None:
                out.append(d)
    return sorted(out)


def next_occurrence(entry, today):
    """오늘 포함, 다음 발생일. (당일이면 오늘을 돌려준다 = D-DAY)"""
    for d in occurrences(entry, today.year - 1, 4):
        if d >= today:
            return d
    return None


def origin_date(entry):
    """원년(출생/결혼) 양력 날짜. 음력이고 원년 미상이면 None."""
    if entry["calendar"] == "solar":
        return entry["date"]
    y = entry.get("origin_year")
    if not y:
        return None
    return lunar_to_solar(y, entry["lunar_month"], entry["lunar_day"],
                          entry.get("lunar_leap", False))


def count_label(entry, when):
    """when 시점의 만 나이 / 몇 주년. 원년을 모르면 빈 문자열."""
    origin = origin_date(entry)
    if origin is None:
        return ""
    n = when.year - origin.year
    if entry["type"] == "anniversary":
        return f"{n}주년"
    return f"만 {n}세"


def who_label(entry):
    """이름/관계 표시. 예: (박혜상·아내), (아버지)"""
    parts = [entry[k] for k in ("name", "relation") if entry.get(k)]
    return f"({'·'.join(parts)})" if parts else ""


def dday_label(days):
    return "D-DAY" if days == 0 else f"D-{days}"


def rows(data, today, group=None, within=None):
    out = []
    for e in data["ddays"]:
        if group and e["group"] != group:
            continue
        nxt = next_occurrence(e, today)
        if nxt is None:
            continue
        days = (nxt - today).days
        if within is not None and days > within:
            continue
        out.append({
            "entry": e,
            "next": nxt,
            "days": days,
            "dday": dday_label(days),
            "weekday": WEEKDAYS[nxt.weekday()],
            "count": count_label(e, nxt),
            "who": who_label(e),
        })
    out.sort(key=lambda r: (r["days"], r["entry"]["title"]))
    return out


def cmd_list(data, args, today):
    rs = rows(data, today, args.group, args.within)
    groups = data["groups"]
    print(f"기준일: {today.isoformat()}({WEEKDAYS[today.weekday()]})  ·  {len(rs)}건\n")
    for r in rs:
        e = r["entry"]
        if e["calendar"] == "lunar":
            src = f"음력 {e['lunar_month']:02d}.{e['lunar_day']:02d}"
        else:
            src = e["date"].strftime("%Y.%m.%d")
        extra = f"  {r['count']}" if r["count"] else ""
        title = f"{e['title']} {r['who']}".strip()
        print(f"{r['dday']:>7}  {r['next']}({r['weekday']})  {title:<32} "
              f"[{groups[e['group']]}]  원본 {src}{extra}")
    return 0


def cmd_check(data, args, today):
    problems = []
    seen = set()
    for e in data["ddays"]:
        if e["id"] in seen:
            problems.append(f"{e['id']}: id 중복")
        seen.add(e["id"])
        if e["group"] not in data["groups"]:
            problems.append(f"{e['id']}: 알 수 없는 group '{e['group']}'")
        if e["calendar"] == "solar":
            if not isinstance(e.get("date"), dt.date):
                problems.append(f"{e['id']}: date 가 YYYY-MM-DD 가 아님")
        elif e["calendar"] == "lunar":
            if next_occurrence(e, today) is None:
                problems.append(f"{e['id']}: 음력 날짜를 양력으로 변환할 수 없음")
        else:
            problems.append(f"{e['id']}: calendar 는 solar 또는 lunar 여야 함")

    n = len(data["ddays"])
    if data["meta"].get("count") != n:
        problems.append(f"meta.count({data['meta'].get('count')}) != 실제 항목 수({n})")

    if problems:
        print("문제 발견:")
        for p in problems:
            print("  -", p)
        return 1
    print(f"이상 없음. {n}건, 기준일 {today.isoformat()}")
    return 0


def fold(line):
    """RFC 5545 줄 접기 (75 octet). 한글이 잘리지 않도록 UTF-8 바이트 단위로."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    out, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        limit = 75 if not out else 74  # 이어지는 줄은 앞에 공백 1칸이 붙는다
        if len(cur) + len(b) > limit:
            out.append(cur)
            cur = b""
        cur += b
    out.append(cur)
    return "\r\n ".join(s.decode("utf-8") for s in out)


def cmd_ics(data, args, today):
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    L = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ilmo//dday//KO",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:기념일",
        "X-WR-TIMEZONE:Asia/Seoul",
    ]

    def event(uid, start, summary, desc, rrule=None):
        L.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}@ilmo",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{start:%Y%m%d}",
            f"DTEND;VALUE=DATE:{start + dt.timedelta(days=1):%Y%m%d}",
            fold(f"SUMMARY:{summary}"),
            fold(f"DESCRIPTION:{desc}"),
            "TRANSP:TRANSPARENT",
        ])
        if rrule:
            L.append(rrule)
        L.extend([
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "TRIGGER:PT9H",          # 당일 오전 9시
            fold(f"DESCRIPTION:{summary}"),
            "END:VALARM",
            "END:VEVENT",
        ])

    n = 0
    for e in data["ddays"]:
        gname = data["groups"][e["group"]]
        if e["calendar"] == "solar":
            first = next_occurrence(e, today)
            desc = f"{gname}{who_label(e) and ' ' + who_label(e)} · 원본 {e['date']:%Y.%m.%d} (양력)"
            event(e["id"], first, e["title"], desc, "RRULE:FREQ=YEARLY")
            n += 1
        else:
            src = f"음력 {e['lunar_month']:02d}.{e['lunar_day']:02d}"
            for d in occurrences(e, today.year, args.years):
                if d < today:
                    continue
                desc = f"{gname}{who_label(e) and ' ' + who_label(e)} · 원본 {src} (음력에서 매년 변환)"
                event(f"{e['id']}-{d:%Y}", d, e["title"], desc)
                n += 1

    L.append("END:VCALENDAR")
    out = Path(args.output) if args.output else ROOT / "dist" / "ddays.ics"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\r\n".join(L) + "\r\n", encoding="utf-8")
    print(f"{out.relative_to(ROOT)} 생성 · VEVENT {n}개 · 음력 {args.years}년치")
    return 0


def main():
    p = argparse.ArgumentParser(description="기념일 D-day 계산기")
    p.add_argument("--on", metavar="YYYY-MM-DD", help="기준일 (기본: 오늘, Asia/Seoul)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="D-day 목록")
    pl.add_argument("--group")
    pl.add_argument("--within", type=int, metavar="N", help="N일 안에 오는 것만")

    sub.add_parser("check", help="데이터 검증")

    pi = sub.add_parser("ics", help="ICS 캘린더 파일 생성")
    pi.add_argument("--years", type=int, default=10, help="음력 항목을 몇 년치 펼칠지 (기본 10)")
    pi.add_argument("-o", "--output")

    args = p.parse_args()
    if args.on:
        today = dt.date.fromisoformat(args.on)
    else:
        today = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)).date()

    data = load()
    return {"list": cmd_list, "check": cmd_check, "ics": cmd_ics}[args.cmd](data, args, today)


if __name__ == "__main__":
    sys.exit(main())
