# KG v2 Neo4j 시각화

KG v2를 로컬 Neo4j의 `KGv2Node` 네임스페이스에 적재했다. 기존 `KGNode` 그래프는 삭제하거나 덮어쓰지 않았다. 25,750개 노드, 35,308개 관계의 ID·유형·양 끝점·속성이 원본 `graph.json`과 정확히 일치함을 검증했다.

- [전체 구성 PNG](schema.png): 모든 노드 유형과 관계 유형을 집계한 구조도다. 상자 하나가 실제 단일 노드를 뜻하지 않는다. 표현 사이의 9종 관계는 한 화살표로 집계했다. 상세 수치는 [유형별 집계](schema_counts.json)에 있다.
- [먹다→묵다→묵고 상세 PNG](eating_path.png): 실제 두 진술의 표현·활용 관계·조건·원문 인용·페이지·문헌을 표시한다. 인용 표시는 공간상 줄였으며 전체 속성은 Neo4j에 보존했다.
- 확대용 SVG: [전체 구성](schema.svg), [상세 연결](eating_path.svg).
- [검증 결과](verification.json), [부분 그래프 데이터](eating_path.json), [Browser 조회문](inspection.cypher).

PNG는 **실제 Neo4j 조회 결과를 Graphviz로 렌더링한 그림**이다. Neo4j Browser 화면 캡처는 아니다. Browser에서는 `http://127.0.0.1:17474/browser/`에 접속한 뒤 조회문을 실행해 직접 노드를 펼칠 수 있다. 로컬 인증 정보는 기존 비공개 runtime 파일에 있으며 보고서에 포함하지 않는다.

같은 ‘묵다’라도 어휘 대응 진술의 목표 표현과 활용 진술의 출발 표현은 서로 다른 출처별 표현 노드다. 두 지식 진술을 잇는 `candidate_has_inflection`이 조회 경로를 만든다. 조건과 원문 근거는 각 진술에 따로 연결되므로 연결만으로 의미·지역·높임의 일치를 승인하지 않는다.

재현: 서비스가 실행 중인 상태에서 `python kg_v2/neo4j_export.py`. 기존 스냅샷을 삭제하지 않는 멱등 적재이며 PNG와 SVG를 다시 생성한다. Neo4j 시작 명령은 `python current_kg/grammar/neo4j_view.py start`이다.
