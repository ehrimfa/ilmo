# 기념일 관리 규칙 (비서용)

이 저장소는 가족 기념일 14건을 관리한다. 아래 규칙을 지켜라.

## 핵심 규칙

1. **정본은 `data/ddays.yaml` 하나뿐이다.** 기념일을 추가·수정·삭제할 때는 이 파일만 고친다.
2. **D-day 숫자를 문서·메모·대화에 적어 저장하지 마라.** 하루만 지나도 틀린다.
   "며칠 남았어?" 류의 질문에는 반드시 스크립트를 실행해서 답한다.
3. **음력 생신 4건은 매년 양력 날짜가 달라진다.** 작년 날짜를 재사용하지 말고 항상 변환한다.
   변환은 `korean_lunar_calendar` 라이브러리가 담당하며, 스크립트가 알아서 처리한다.
4. `data/ddays.yaml` 을 고쳤으면 **`check` → `ics` 순서로 실행**하고 결과를 커밋한다.

## 명령어

```bash
pip install -r requirements.txt        # 최초 1회

python3 scripts/dday.py list           # 전체 목록 (D-day 오름차순)
python3 scripts/dday.py list --within 30       # 30일 안에 오는 것만
python3 scripts/dday.py list --group ours      # 그룹별 (ours/parents/parents_in_law/junhui/unsorted)
python3 scripts/dday.py check          # 데이터 검증 — 수정 후 반드시 실행
python3 scripts/dday.py ics --years 10 # dist/ddays.ics 재생성
python3 scripts/dday.py --on 2027-01-01 list   # 특정 날짜 기준으로 조회
```

기준일은 기본적으로 **Asia/Seoul 기준 오늘**이다. `--on` 은 검증·미리보기용.

## Google 캘린더 연동

14건은 이미 사용자의 기본 캘린더(nayoonghee78@gmail.com)에 올라가 있다.
어디에 무엇이 들어갔는지는 **`data/calendar.yaml`** 에 적혀 있다. 세 갈래다.

| 갈래 | 건수 | 방식 |
|---|---|---|
| 음력 생신 | 4 | 한 일정 + `RDATE` 로 발생일 나열 (2036~2037년까지) |
| 양력 생일·결혼기념일 | 8 | `RRULE:FREQ=YEARLY` — 자동 반복, 손댈 일 없음 |
| 기존 생일 일정 | 2 | 예전부터 있던 `BIRTHDAY` 유형 일정 (정희현, 나영후) |

지킬 것:

1. **캘린더 일정을 새로 만들지 마라.** `data/calendar.yaml` 의 `event_id` 를 update 해야 한다.
   새로 만들면 같은 기념일이 두 번 뜬다.
2. **`from_contacts` 2건(정희현·나영후)은 새로 만들지 마라.** 이미 `BIRTHDAY` 유형 일정으로 있다.
   단, `BIRTHDAY` 유형은 **날짜 수정도 생성도 API 로 막혀 있다**("invalid argument"). 날짜를 고쳐야 하면
   일반 일정으로 새로 만들고 옛 일정을 지우는 수밖에 없다 (나준희 건에서 그렇게 처리했다).
3. **종일 일정의 날짜는 `Z` 로 넘겨라.** `2026-10-23T00:00:00Z` 처럼. `+09:00` 오프셋을 쓰면
   UTC 로 환산되면서 하루 당겨진다(실제로 겪었다).
4. **음력 4건은 `through` 연도가 다가오면 갱신해야 한다.** `scripts/dday.py` 로 다음 발생일을
   다시 뽑아 RDATE 를 늘려주면 된다.
5. **같은 사람이 두 번 뜨지 않게 하라.** 등록 전에 반드시 기존 일정을 먼저 조회한다.
   2026-08-31 에 중복 4건을 정리했고 목록은 `data/calendar.yaml` 의 `removed_duplicates` 에 있다.

## 데이터 스키마

```yaml
- id: mother-birthday        # 영문 소문자-하이픈, 고유값. 한번 정하면 바꾸지 않는다(ICS UID 로 쓰임)
  title: "어머니 생신"          # 앱/캘린더에 표시되는 이름. ICS SUMMARY 로 쓰이므로 함부로 바꾸지 않는다
  name: "박혜상"               # (선택) 실명. 모르면 생략
  relation: "아내"             # (선택) 관계. title 만으로 알 수 있으면 생략한다
  type: birthday             # birthday(생일·생신) | anniversary(결혼기념일) | birth(탄생)
  group: parents             # ours | parents(본가) | parents_in_law(처가) | junhui
  calendar: lunar            # solar | lunar
  # calendar: solar 이면 ↓
  date: 1981-11-07           # 양력 원본 날짜 (YYYY-MM-DD)
  # calendar: lunar 이면 ↓
  lunar_month: 4
  lunar_day: 29
  lunar_leap: false          # 윤달이면 true
  origin_year: 1956          # 원년(출생연도, 음력 기준). 모르면 null → 나이 계산이 생략된다
```

`type` 은 표시 문구를 결정한다: `anniversary` 는 "N주년", 나머지는 "만 N세".
`origin_year` 가 `null` 인 음력 4건은 나이가 계산되지 않는다 — 출생연도를 알게 되면 채워 넣어라.

## 새 기념일 추가 절차

1. `data/ddays.yaml` 의 `ddays:` 에 항목 추가 (해당 그룹 블록 안에)
2. `meta.count` 를 실제 개수에 맞게 수정
3. `python3 scripts/dday.py check` 통과 확인
4. `python3 scripts/dday.py ics --years 10` 으로 `dist/ddays.ics` 재생성
5. 커밋

## 가족 관계

기준이 되는 본인은 **나융희**다. 아래 관계는 전부 이분 기준.

- **우리 가족**: 아내 **박혜상**(1981.11.07), 자녀 **나은혜**(2014.05.31)·**나혜림**(2017.05.02),
  결혼기념일 2012.09.07
- **본가**: 아버지 **나정평**(음력 1955.03.20)·어머니 **김광순**(음력 1956.04.29),
  결혼기념일 1978.01.27
- **처가**: 장인어른/아버님 **박철완**(음력 1950.05.11)·장모님/어머님 **오려옥**(음력 1955.09.13),
  결혼기념일 1980.04.12, 처남 **박진호**(1984.03.23)
- **준희네**: 남동생 **나준희**(1980.08.31), 제수씨 **정희현**(1979.09.03),
  조카 **나영후**(2011.03.06)

## 확인이 필요한 항목

현재 14건의 이름·관계·출생연도가 모두 확인되어 비어 있는 항목은 없다.
새 기념일을 추가할 때 관계나 연도를 모르면 임의로 단정하지 말고 사용자에게 물어라.

## 데이터 출처와 검증

더데이비포(the day before) 앱 화면 캡처 2장(2026-08-31 KST 기준)에서 옮겼다. 옮긴 직후:

- 양력 10건의 **요일이 앱 표시와 전부 일치**함을 확인했다.
- 14건의 **D-day 계산값이 앱 표시와 전부 일치**함을 확인했다
  (D-DAY, 3, 7, 53, 68, 149, 187, 204, 224, 238, 244, 273, 276, 288).

데이터 구조를 바꿨다면 `--on 2026-08-31 list` 로 위 숫자가 그대로 나오는지 확인하면
회귀 여부를 알 수 있다.
