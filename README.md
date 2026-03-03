# AI Briefings

매일 아침 7시에 AI/기술 관련 주요 뉴스와 지식을 정리하여 이 레포에 커밋합니다.

## 구조
- `daily/YYYY-MM-DD.md`: 일일 요약 콘텐츠
- `monthly/YYYY-MM.md`: 월 단위 요약/핵심 흐름
- `state/YYYY-MM.json`: 수집한 항목(링크/ID) 기록
- `logs/YYYY-MM.log`: 수집 실패/에러 정리
- `scripts/collect_news.py`: 피드 → 요약 → 상태 업데이트 자동화 스크립트

## 작업 흐름
1. `feeds.json`에 정리한 URL 목록을 기반으로 수집
2. 스크립트가 하루 한 번 새 소스를 가져와 `daily/`와 `monthly/`에 Markdown 작성
3. 상태(State)와 로그(Log)를 갱신하고 git 커밋 + 푸시
4. 매일 7시에 요약 알림(메시지 + GitHub 링크)

## Feeds to monitor
| Region | Type | Title | URL | Notes |
| --- | --- | --- | --- | --- |
| Global | RSS | AIFeed | https://aifeed.dev/feed.xml | 영어 콘텐츠는 자연스럽게 한국어로 번역, 중요한 단어는 영어 유지 (필요시 괄호 안에 영어도 함께)

이 목록은 `feeds.json`으로도 관리되며 필요한 채널을 추가/수정하면 곧바로 스크립트가 대응합니다.

## 자동화
- `scripts/collect_news.py`는 RSS/YouTube 피드를 읽고 최신 항목을 `daily/`/`monthly/`로 저장합니다.
- 중복 방지를 위해 `state/YYYY-MM.json`에 링크 해시를 누적합니다. 실패한 피드/URL은 `logs/YYYY-MM.log`에 이유와 함께 남겨서 대체 루트를 찾을 수 있게 합니다.
- 필요하면 `scripts/collect_news.py`를 cron이나 heartbeat로 하루 1회 실행하면 전체 흐름이 자동화됩니다.
