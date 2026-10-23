# KG v2

7종·474쪽의 문헌을 바탕으로 작성한 방언 지식이다. 현재 규모는 **지식 항목 3,767개 / 노드 25,818개 / 관계 35,410개**이며, 각각 9개 내용 유형·8개 노드 유형·19개 관계 유형을 사용한다.

전체 과정과 생성 결과는 [통합 보고서](../reports/20261021_paper50/report.html), 상세 작성 규격은 [AUTHORING.md](AUTHORING.md)를 따른다.

| 파일·폴더 | 역할 |
|---|---|
| `source_registry.json` | 원문 7종의 위치·쪽수·출처 |
| `authored/`, `reviews/` | 원문 근거를 포함한 지식 작성본과 검토 기록 |
| `facts.jsonl`, `graph.json` | 지식 항목과 같은 정보를 펼친 노드·관계 |
| `sentence_retrieval.py`, `query.py` | 입력 구간에 맞는 항목 검색과 일부 어휘–활용 관계 탐색 |
| `terminal_retrieval.py`, `construction_retrieval.py` | 종결·복합 표현의 적용 조건과 변환안 |
| `transformation_plan.py` | 구간별 후보·보존 지침의 생성 입력 구성 |
| `preservation_check.py` | 생성 후 일부 의미·높임 변화 검사와 최대 1회 수정 |
| `reports/` | 구축·근거 확인 및 이전 연결 실험 기록 |

현재 조회는 항목 직접 검색과 제한적인 관계 탐색을 결합한다. 그래프 전체를 무제한으로 따라가거나 모든 관계를 Qwen에 전달하지 않는다. 최신 50건 실험의 코드·KG 고정 사본은 `../reports/20261021_paper50/snapshot/`에 있다.

## 확인 명령

프로젝트 루트에서 실행한다.

```bash
.venv/retrieval/bin/python kg_v2/query.py --lemma 먹다 --ending=-고
.venv/retrieval/bin/python -m unittest discover -s kg_v2 -p 'test_*.py' -v
```

원문 PDF는 로컬 등록 경로에 별도로 필요하다. PDF 전체 텍스트 추출·KG 재빌드는 데이터 수정 작업이므로 단순 보고서 열람에는 필요하지 않다. 재빌드 절차와 과거 검토 내용은 [정리 전 KG 안내](../archive/research_notes_20261024/kg_v2/README.md)에 보관했다.
