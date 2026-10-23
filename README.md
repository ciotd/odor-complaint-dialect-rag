# 표준어–경상도 방언 변환 연구

문장 분석과 방언 지식을 Qwen에 제공해 표준어를 경상도 방언으로 변환하는 연구입니다. 현재 논문용 비교는 **표준어 50개 × 세 조건**이며, 실험일은 2026년 10월 21일입니다.

**[통합 보고서 열기](reports/20261021_paper50/report.html)** — 연구 배경, 처리 과정, KG 구성, 실험 조건, 결과 그래프와 50개 사례를 한 문서에서 확인합니다. HTML 파일을 내려받아 브라우저에서 열면 결과 전환·검색 기능을 사용할 수 있습니다.

| 확인할 내용 | 파일 |
|---|---|
| 표준어 50개 | [데이터셋 TXT](reports/20261021_paper50/논문용_테스트_데이터셋.txt) |
| 세 조건의 최초·최종 번역 | [번역 TXT](reports/20261021_paper50/translations.txt) · [비교표 TSV](reports/20261021_paper50/comparison.tsv) |
| 논문용 처리 구조도 | [PNG](reports/20261021_paper50/figures/kg_pipeline_K.png) · [SVG](reports/20261021_paper50/figures/kg_pipeline_K.svg) |
| 실행 설정과 원본 기록 | [실험 폴더](reports/20261021_paper50/) |
| 코드와 자료 위치 | [프로젝트 안내](PROJECT_MAP.md) |
| 현행 KG 구성·조회 코드 | [KG 안내](kg_v2/README.md) |

세 조건은 **P: 원문만**, **A: 원문과 문장 분석**, **K: 원문·분석·KG 지식**입니다. 같은 모델과 생성 설정으로 비교했습니다. 표본 구성과 평가 절차는 통합 보고서의 실험 방법에 설명되어 있습니다.

## 보고서 다시 만들기

저장된 결과만 읽으며 모델을 새로 호출하지 않습니다.

```bash
.venv/retrieval/bin/python reports/20261021_paper50/build_report.py
python reports/update_index.py
python reports/20261021_paper50/build_bundle.py
```

생성된 ZIP은 로컬 전달용이며 Git에는 포함하지 않습니다. 보고서의 자료 링크까지 함께 전달하려면 실험 폴더 또는 ZIP을 전달합니다.

## 폴더는 이렇게 구분합니다

| 폴더 | 현재 역할 | 유지 이유 |
|---|---|---|
| `kg_v2/` | 실제 번역에 쓰는 KG와 조회·생성·검사 코드 | 현행 시스템 본체 |
| `current_kg/` | 이전 KG와 현재도 사용하는 공통 분석·호출 코드 | `kg_v2`가 일부 모듈을 가져오며, 구축 검사가 기존 파일 보존을 확인함 |
| `reports/` | 최신 50건 실험 전체, 직전 70건·20건의 핵심 기록 | 결과 확인·재현과 입력 출처 확인 |
| `sources/` | 문헌 등록과 선행연구 정리 | 지식의 출처와 연구 배경 확인 |

`current_kg`라는 이름은 이전 버전에서 남은 이름입니다. 최신 K 조건이 사용하는 지식은 **`kg_v2/facts.jsonl`과 `kg_v2/graph.json`**입니다. `current_kg/README.md`의 수치와 진행 상황은 10월 8일 당시 기록입니다.

과거 구현인 `archive/`, 9월의 미확정 서론 초안인 `paper/`, 중복된 과거 실험 파일은 현재 브랜치에서 제거했습니다. 원본은 [정리 전 커밋](https://github.com/ciotd/odor-complaint-dialect-rag/tree/4d6998be399df717762231fa3ea1c23f17212b85)에 남아 있습니다. 삭제 목록과 유지 이유는 [폴더 검수 기록](reports/repository_audit.json)에 있습니다.

원문 PDF·코퍼스·모델 인증정보는 Git에 포함하지 않습니다. 원문 자료의 위치는 [문헌 등록표](kg_v2/source_registry.json)에 있습니다. 이번 정리에서는 KG·조회·생성 코드를 변경하거나 새 번역을 실행하지 않았습니다.
