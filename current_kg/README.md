# 현재 KG 재구축 작업

## 목표

표준어 문장을 경상도 방언으로 변환할 때 지역·문장 유형·높임·결합 환경·시대·세대를
조건으로 활용할 수 있는 지식그래프를 새로 구축한다.

## 현재 입력 화이트리스트

- `../sources/gyeongsang/academic/경북방언_종결어미_연구.pdf`
- `../sources/gyeongsang/academic/표준어 간섭 및 방언에 대한 의식으로 인한 경남 함양 방언 문법 형태의 변화 연구.pdf`
- `../sources/gyeongsang/web/동남 방언.pdf`

`../sources/gyeongsang/lexical/gyeongsang_vocab.json`은 문법 KG와 분리한 어휘 후보
스냅샷이다.

## 제외

`../archive/v2_failed/`의 종결어미 39규칙·스키마·코드·결과와
`../archive/v1_retrieval/`의 문법·RAG 자료는 신규 Claim 추출에 사용하지 않는다.

## 진행 순서

1. 원문 구간과 표·예문의 위치 고정
2. 문헌별 원자 단위 Claim 독립 추출
3. Claim의 출처·범위·시대·지역 재검사
4. 사용자 승인·수정·기각
5. 문헌 간 일치·충돌 정리
6. 노드·관계 초안 제시 및 상세 설명
7. 승인된 Claim에서 운영 Rule 구성
8. 사람 평가 중심의 평가 설계

현재는 2단계를 시작하기 직전이다.
