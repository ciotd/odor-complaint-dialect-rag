# 경상 문법 규칙 검수 (159개) — 원본 메타데이터
각 규칙 아래 `결정:`에 **유지 / 제거 / 수정: <새 standard→dialect>** 중 하나 적기.
비우면 기본 유지. 다 적은 뒤 저장하면 내가 rule_overrides.json에 반영.

## #1  [GS-00001]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `외, 의, 류`
- **dialect** : `애, 으, 루`
- explanation: 이중모음이 단모음으로 변환
    - 예: 외무부 장관이 발표했다. → 애무부 장관이 발표했다.
    - 예: 의사 선생님이 오셨다. → 으사 선생님이 오셨다.
- keywords: ['음운론', '음운변화', '경상도', '이중모음 단모음화']
- 결정: 유지

## #2  [GS-00002]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `오, 아 (후설모음)`
- **dialect** : `외, 애 (전설모음 i-움라우트)`
- explanation: 후설모음이 전설모음으로 변환 (i-움라우트)
    - 예: 오늘 저녁에는 소고기를 먹자. → 오늘 저녁에는 소괴기를 묵자.
    - 예: 나는 매일 학교에 간다. → 나는 매일 핵교에 간다.
- keywords: ['음운론', '음운변화', '경상도', '전설모음화 (움라우트)']
- 결정: 제거

## #3  [GS-00003]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `여`
- **dialect** : `에`
- explanation: ㅕ가 ㅔ로 발음되거나 풀어짐
    - 예: 경상도 지방에 놀러 가자. → 겡상도 지방에 놀러 가재이.
    - 예: 형님, 오래간만입니다. → 헹님, 오래간만입니더.
- keywords: ['음운론', '음운변화', 'ㅕ→ㅔ 변환', '경상도']
- 결정: 유지

## #4  [GS-00004]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `오늘, 지금, 내일`
- **dialect** : `올, 짐, 낼`
- explanation: 콧소리 자음 등이 단어 중간에서 탈락
    - 예: 오늘 우리 집에 놀러 와. → 올 우리 집에 놀러 오너라.
    - 예: 지금 바로 가겠습니다. → 짐 바로 가겠심더.
- keywords: ['음운론', '음운변화', '경상도', '음 탈락/축약']
- 결정: 유지

## #5  [GS-00005]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `으, 우`
- **dialect** : `어, 으`
- explanation: ㅡ와 ㅓ 발음이 중간음으로 통합 (지역/세대별 편차)
    - 예: 이수근 씨가 방송에 나온다. → 이수건 씨가 방송에 나온다.
    - 예: 은지원 씨가 노래를 부른다. → 언지원 씨가 노래를 부른다.
- keywords: ['음운론', '음운변화', 'ㅡ/ㅓ 구분 약화', '경상도']
- 결정: 유지

## #6  [GS-00006]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-워 (ㅂ 불규칙)`
- **dialect** : `-어 (ㅂ 규칙)`
- explanation: 'ㅂ' 불규칙이 아닌 규칙 활용 (동부 지역)
    - 예: 오늘 날씨가 너무 더워요. → 오늘 날씨가 너무 덥어요.
    - 예: 밖이 너무 추워요. → 밖이 너무 춥어요.
- keywords: ['음운론', '음운변화', '경상도', 'ㅂ 규칙 활용']
- 결정: 

## #7  [GS-00007]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `ㄱ, ㅂ, ㄷ, ㅅ, ㅈ (예사소리)`
- **dialect** : `ㄲ, ㅃ, ㄸ, ㅆ, ㅉ (된소리)`
- explanation: 첫음절 강세로 자음이 된소리화
    - 예: 과자를 많이 먹으면 이가 썩는다. → 까자를 많이 묵으모 이가 썩는다.
    - 예: 내 속이 다 시원하다. → 내 쏙이 다 시원하다.
- keywords: ['음운론', '음운변화', '경상도', '첫음절 경음화']
- 결정: 유지

## #8  [GS-00008]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-습니다, -생`
- **dialect** : `-시엄니다, -섕 (구개음화 변이)`
- explanation: ㅅ이 일부 발음에서 구개음화 (화자/지역별 편차)
    - 예: 저는 당신을 믿습니다. → 나는 당신을 믿쉬엄니다.
    - 예: 그는 모범적인 학생이다. → 지는 모범적인 학섕이다.
- keywords: ['음운론', '음운변화', 'ㅅ 구개음화', '경상도']
- 결정: 제거

## #9  [GS-00009]  (판정설명의문규칙)
- speech_level: 하라체 | sentence: 의문형 | tense: 현재
- **standard**: `-니, -는가, -어`
- **dialect** : `-나, -노, -가, -고`
- explanation: 판정 의문문(예/아니오)=ㅏ계열(-나,-가), 설명 의문문=ㅗ계열(-노,-고). 용언→ㄴ계열, 체언→ㄱ계열
    - 예: 너 밥 먹었니? → 니 밥 뭇나?
    - 예: 너 뭐 먹었니? → 니 머 뭇노?
- keywords: ['종결형', '의문 종결 어미 -나/-노/-가/-고', '경상도', '문법론']
- 결정: 유지

## #10  [GS-00010]  (문법론)
- speech_level: 하라체 | sentence: 평서형 | tense: 현재
- **standard**: `-라고 하다, 왜 그래`
- **dialect** : `-라카다, 와 카노`
- explanation: '그러다/그라다'→'카다', '-라고 하다'→'-라카다'
    - 예: 너 왜 그래? → 니 와 카노?
    - 예: 그 사람이 뭐라고 하니? → 그 사람이 머라카노?
- keywords: ['종결형', '-카다/-쿠다 (하다/그러다 축약)', '경상도', '문법론']
- 결정: 제거 (반말이라서)

## #11  [GS-00011]  (문법론)
- speech_level: 하라체 | sentence: 평서형 | tense: 현재
- **standard**: `들어가다, 내버리다, 일어나다`
- **dialect** : `드가다, 내삐다, 일나다`
- explanation: 표준어와 다른 활용 형태
    - 예: 방으로 어서 들어가라. → 방으로 퍼뜩 드가거라.
    - 예: 쓰레기를 길가에 내버리지 마라. → 쓰레기를 길가에 내삐리지 마라.
- keywords: ['종결형', '불규칙 파생 용언', '경상도', '문법론']
- 결정: 제거 ( 이건 문법이 아니잖아)

## #12  [GS-00012]  (문법론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: ` -만큼, -처럼, -보다, -까지, -니까`
- **dialect** : ` -맨키, -맨치로, -보도, -꺼지, -이끼네`
- explanation: 표준어 조사의 방언 형태
    - 예: 나한테 전화를 해라. → 내인데 전화를 해라.
    - 예: 우리 형처럼 되고 싶다. → 우리 헹님맨치로 되고 싶다.
- keywords: ['종결형', '조사 변환', '경상도', '문법론']
- 결정: 수정 -한테 -> -인데만 제거

## #13  [GS-00013]  (경어법)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-어, -십시오`
- **dialect** : `-대이`
- explanation: 평서/명령/청유에서 조심스러운 뉘앙스. 격식적이지 않으나 공손함 포함
    - 예: 그 말이 맞습니다. → 그 말이 맞대이.
    - 예: 내일 또 오세요. → 내일 또 배이시대이.
- keywords: ['-대이 용법', '경어법', '경상도', '높임표현']
- 결정: 유지

## #14  [GS-00014]  (경어법)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-습니다, -습니까, -하십시오, -읍시다`
- **dialect** : `-(스)ㅂ니다/-(스)ㅂ니더, -(스)ㅂ니까/-(스)ㅂ니꺼, -이소/-주이소, -입시다`
- explanation: 표준어 하십시오체에 대응. -(스)ㅂ니다/-ㅂ니꺼
    - 예: 안녕하십니까? → 안녕합니꺼?
    - 예: 여기 앉으십시오. → 요기 앉으이소.
- keywords: ['경어법', '경상도', '하이소체 (최상위 존대)', '높임표현']
- 결정: 유지

## #15  [GS-00015]  (경어법)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-어요, -이어요`
- **dialect** : `어미 -어예, -이라예`
- explanation: 표준어 해요체에 대응. -예/-요 첨사
    - 예: 그것이 맞아요. → 그기 맞아예.
    - 예: 저는 학생이에요. → 나는 학생이라예.
- keywords: ['경어법', '해예/해요체', '경상도', '높임표현']
- 결정: 유지

## #16  [GS-00016]  (경어법)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-소, -나요, -는가요`
- **dialect** : `-소, -는교, -는기요`
- explanation: 표준어 하오체에 대응. 지역별 차이 큼
    - 예: 이리 오시오. → 이리 오소.
    - 예: 어디 가나요? → 어데 가는교?
- keywords: ['하소체', '경어법', '경상도', '높임표현']
- 결정: 유지

## #17  [GS-00017]  (경어법)
- speech_level: 하라체 | sentence: 평서형 | tense: 현재
- **standard**: `-네, -이네, -는가`
- **dialect** : `-네, -(이)ㄷ세, -는공/-는고`
- explanation: 거의 사멸. 70대 이상만 사용
    - 예: 자네 오늘 기분이 아주 좋아 보이네. → 자네 오늘 기분이 억수로 좋아 보이네.
    - 예: 그가 내 친구이네. → 지가 내 친구ㄷ세.
- keywords: ['하게체', '경어법', '경상도', '높임표현']
- 결정: 제거

## #18  [GS-00018]  (경어법)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-어, -지, -니, -이냐`
- **dialect** : `-어, -지, -나/-노, -(이)가/-(이)고`
- explanation: 표준어 해체에 대응
    - 예: 나 먼저 갈게. → 내 먼저 갈게.
    - 예: 너 지금 뭐 하니? → 니 지금 머 하노?
- keywords: ['해체 (반말)', '경어법', '경상도', '높임표현']
- 결정: 유지

## #19  [GS-00019]  (경어법)
- speech_level: 하라체 | sentence: 평서형 | tense: 현재
- **standard**: `-다, -니, -아라, -거라`
- **dialect** : `-다, -나/-노, -아라, -거라`
- explanation: 표준어 해라체에 대응
    - 예: 철수가 밥을 먹는다. → 철수가 밥 묵는다.
    - 예: 너 어제 어디 갔었니? → 니 어제 어데 갔었노?
- keywords: ['해라체', '경어법', '경상도', '높임표현']
- 결정: 유지

## #20  [GS-00020]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `길, 힘, 흉 (구개음화)`
- **dialect** : `질, 심, 숭`
- explanation: 어두 위치에서 i/j 앞의 ㄱ→ㅈ/ㅉ/ㅊ, ㅎ→ㅅ/ㅆ 변환. 고유어·한자어 거의 예외 없음. 출처: 한국민족문화대백과
    - 예: 길이 좁아서 운전하기 힘들다. → 질이 좁아가 운전하기 심들다.
    - 예: 저 사람은 힘이 세다. → 저 사람은 심이 시다.
- keywords: ['음운론', '음운변화', 'ㄱ/ㅎ 구개음화', '경상도']
- 결정: 유지

## #21  [GS-00021]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `꽃, 낯, 빛 (치조폐쇄음)`
- **dialect** : `꼳, 낱, 빋`
- explanation: 명사 어간말 파찰음 ㅊ→ㅌ 변환. 동남방언에는 어간말 ㅊ을 가진 명사가 거의 없음. 출처: 한국민족문화대백과
    - 예: 길가에 예쁜 꽃이 피었다. → 질가에 이쁜 꼳이 피었다.
    - 예: 아는 낯이 있구나. → 아는 낱이 있구나.
- keywords: ['음운론', '음운변화', 'ㅊ 치조폐쇄음화', '경상도']
- 결정: 유지  (⚠방언형 확인(음운 정확성))

## #22  [GS-00022]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-하고 (유기음화)`
- **dialect** : `-하고 (연음화)`
- explanation: 명사 어간말 ㅂ/ㄷ/ㄱ + 어미 첫음 ㅎ 결합 시 유기음화가 일어나지 않음 (표준어와 다름). 출처: 한국민족문화대백과
    - 예: 밥하고 국을 먹었다. → 밥하고 국을 묵었다.
    - 예: 꽃하고 나무를 심었다. → 꼬다고 나무를 심었다.
- keywords: ['음운론', '음운변화', '유기음화 미발생', '경상도']
- 결정: 유지  (⚠방언형 확인(음운 정확성))

## #23  [GS-00023]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `쌀`
- **dialect** : `살`
- explanation: 낙동강 동쪽 지역에서 ㅆ(s)가 음소 기능 없음. ㅆ과 ㅅ이 구별되지 않음. 출처: 한국민족문화대백과
    - 예: 쌀을 깨끗하게 씻어라. → 살을 깨끗하게 씻어라.
- keywords: ['음운론', '음운변화', '경상도', 'ㅆ/ㅅ 미구별 (낙동강 이동)']
- 결정: 유지  (⚠방언형 확인(음운 정확성))

## #24  [GS-00024]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `모음체계 (6/7/8모음)`
- **dialect** : `동남방언은 6모음체계가 일반적(i,ε,ɔ,a,u,o). 지역/세대에 따라 7모음(+ə) 또는 8모음(+e,ə). 6모음에서 ㅔ/ㅐ, ㅗ/ㅓ 미구별. 출처: 한국민족문화대백과`
- explanation: 동남방언은 6모음체계가 일반적(i,ε,ɔ,a,u,o). 지역/세대에 따라 7모음(+ə) 또는 8모음(+e,ə). 6모음에서 ㅔ/ㅐ, ㅗ/ㅓ 미구별. 출처: 한국민족문화대백과
- keywords: ['음운론', '음운변화', '모음체계 (6/7/8모음)', '경상도']
- 결정: 제거

## #25  [GS-00025]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `성조 체계`
- **dialect** : `동남방언은 성조방언. 어두음절에서 단어 뜻 분화. word pitch 자격. 출처: 한국민족문화대백과`
- explanation: 동남방언은 성조방언. 어두음절에서 단어 뜻 분화. word pitch 자격. 출처: 한국민족문화대백과
- keywords: ['음운론', '음운변화', '경상도', '성조 체계']
- 결정: 제거

## #26  [GS-00026]  (문법론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-으면`
- **dialect** : `-으모/-으몬(경남서남), -으마/-으만/-으머/-으면`
- explanation: 표준어 접속어미의 동남방언 변이형. 출처: 한국민족문화대백과
    - 예: -으면 → -으모/-으몬(경남서남), -으마/-으만/-으머/-으면
    - 예: -으면서 → -음서(경남서남), -으먼서/-으민서
- keywords: ['종결형', '접속어미 방언형', '경상도', '문법론']
- 결정: 불확실  (어휘면 제거·조사/어미면 유지 → 확인)

## #27  [GS-00027]  (경어법)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `지역별 하이소체 어미 -으십시오`
- **dialect** : `하이소체 변이 -으이소, -으시이소`
- explanation: 하이소체의 지역별 세부 형태. 출처: 한국민족문화대백과
    - 예: 이리 오십시오. → 이리 오이소.
    - 예: 이리 오십시오. → 이리 오시이소.
- keywords: ['하이소체 지역별 변이 (상세)', '경어법', '경상도', '높임표현']
- 결정: 유지  (경어법(존댓말) 유지)

## #28  [GS-00028]  (경어법)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `지역별 하소체 어미 -으오`
- **dialect** : `하소체 변이 -으소`
- explanation: 하소체의 지역별 세부 형태. 출처: 한국민족문화대백과
    - 예: 아무도 없소. → 아무도 없소.
    - 예: 빨리 가오. → 퍼뜩 가소.
- keywords: ['경어법', '하소체 지역별 변이 (상세)', '경상도', '높임표현']
- 결정: 유지  (경어법(존댓말) 유지)

## #29  [GS-00029]  (음운론)
- speech_level: 하라체 | sentence: 평서형 | tense: 현재
- **standard**: `과자`
- **dialect** : `가자`
- explanation: 경북방언에서 어두에 자음이 있으면 이중모음이 단모음으로 발음됨. 자음 없는 어두에서만 이중모음 실현. 출처: 경북방언 특징
    - 예: 과자 → 가자
    - 예: 꿩 → 꽁
- keywords: ['음운론', '음운변화', '자음 뒤 이중모음→단모음화 (경북)', '경상도']
- 결정: 유지  (⚠방언형 확인(음운 정확성))

## #30  [GS-00030]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `메느리`
- **dialect** : `미느리`
- explanation: e가 i로 바뀌는 현상. 이중모음이 단모음화된 ye>e도 i로 변함. 출처: 경북방언 특징
    - 예: 며느리 → 미느리
    - 예: 세금 → 시금
- keywords: ['음운론', '음운변화', '경상도', 'e>i 변화 (경북)']
- 결정: 유지  (⚠방언형 확인(음운 정확성))

## #31  [GS-00031]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `앓아도`
- **dialect** : `앍아도`
- explanation: 비어두음절에서 중부방언 h에 대해 k로 대응. 중세어 '바회→바위' 등과 관련. 출처: 경주방언 특징
    - 예: 앓아도 → 앍아도
    - 예: 닳아도 → 닭아도
- keywords: ['음운론', '음운변화', '어말자음 h→k 대응 (경북)', '경상도']
- 결정: 유지  (⚠방언형 확인(음운 정확성))

## #32  [GS-00032]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `바꾸고`
- **dialect** : `바꿎꼬(60대 이하) / 바꾸우고`
- explanation: 2음절 어간(Cu:) 동사에서 장음 삭제 후 h 첨가. 바꾸(Cu:)→바꿎(Cuh). 출처: 경주방언 특징
    - 예: 60대 이상 → 바꿎꼬(60대 이하) / 바꾸우고
    - 예: 바꾸더라 → 바꿎떠라
- keywords: ['음운론', '음운변화', '장음삭제+h첨가 (경주, 60대 이하)', '경상도']
- 결정: 유지  (⚠방언형 확인(음운 정확성))

## #33  [GS-00033]  (음운론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `모음조화 지역차 (경북)`
- **dialect** : `부동사형어미 -아/어의 모음조화가 지역별로 다름. 출처: 경북방언 특징`
- explanation: 부동사형어미 -아/어의 모음조화가 지역별로 다름. 출처: 경북방언 특징
- keywords: ['음운론', '음운변화', '모음조화 지역차 (경북)', '경상도']
- 결정: 유지  (⚠방언형 확인(음운 정확성))

## #34  [GS-00034]  (문법론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `주격조사 -이가/-(이)란 (경북)`
- **dialect** : `경북방언에서 주격조사 -이/가는 음운론적 조건에 의한 변이형이 아님. 존칭 주격 -께서 대신 -이/가 사용. -이가, -(이)란도 존재. 출처: 경북방언 특징`
- explanation: 경북방언에서 주격조사 -이/가는 음운론적 조건에 의한 변이형이 아님. 존칭 주격 -께서 대신 -이/가 사용. -이가, -(이)란도 존재. 출처: 경북방언 특징
    - 예: 발바닥이 아파서 → 발빠댁이가 아파가주
    - 예: 학교에서 지금 나오라고 한다 → 학교어서 시방 나오라 칸다
- keywords: ['종결형', '주격조사 -이가/-(이)란 (경북)', '경상도', '문법론']
- 결정: 불확실  (어휘면 제거·조사/어미면 유지 → 확인)

## #35  [GS-00035]  (문법론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `속격조사 -에/-으/-이 (경북)`
- **dialect** : `표준어 -의에 대응하는 경북방언 속격조사. 화석형 -오/-우도 존재. 출처: 경북방언 특징`
- explanation: 표준어 -의에 대응하는 경북방언 속격조사. 화석형 -오/-우도 존재. 출처: 경북방언 특징
    - 예: 나의 살던 고향은 → 나에 살던 고향은
    - 예: 자식의 도리를 해야지 → 자석으 도리로 해야지
- keywords: ['종결형', '속격조사 -에/-으/-이 (경북)', '경상도', '문법론']
- 결정: 불확실  (어휘면 제거·조사/어미면 유지 → 확인)

## #36  [GS-00036]  (문법론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `공동격조사 -카/-캉 (경북)`
- **dialect** : `표준어 -와/-과에 대응. -하고도 사용. 출처: 경북방언 특징`
- explanation: 표준어 -와/-과에 대응. -하고도 사용. 출처: 경북방언 특징
    - 예: 너는 나와 같이 놀자 → 니는 내캉 같이 놀재이
    - 예: 너는 나와 같이 놀자 → 니는 내카 같이 놀재이
- keywords: ['종결형', '경상도', '문법론', '공동격조사 -카/-캉 (경북)']
- 결정: 불확실  (어휘면 제거·조사/어미면 유지 → 확인)

## #37  [GS-00037]  (문법론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `선어말어미 -앗-/-것- (경북)`
- **dialect** : `표준어 과거 -았-은 -앗-으로, 추측 -겠-은 -것-으로 실현. 출처: 경북방언 특징`
- explanation: 표준어 과거 -았-은 -앗-으로, 추측 -겠-은 -것-으로 실현. 출처: 경북방언 특징
    - 예: 못 살았어 → 그때는 정말 몯 살앗어
    - 예: 내일 가겠어? → 내앨 가것어?
- keywords: ['종결형', '선어말어미 -앗-/-것- (경북)', '경상도', '문법론']
- 결정: 불확실  (어휘면 제거·조사/어미면 유지 → 확인)

## #38  [GS-00038]  (문법론)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `부정법 몬/몯 + 단형 선호 (경북)`
- **dialect** : `표준어 '못'은 '몬/몯'으로 사용. 서술어 종류 상관없이 단형부정(안 X)이 장형(X지 않다)보다 훨씬 많이 사용됨. '그렇지 않다'→'글찬타'만 축약형 존재. 출처: 경북방언 특징`
- explanation: 표준어 '못'은 '몬/몯'으로 사용. 서술어 종류 상관없이 단형부정(안 X)이 장형(X지 않다)보다 훨씬 많이 사용됨. '그렇지 않다'→'글찬타'만 축약형 존재. 출처: 경북방언 특징
    - 예: 가지 않겠다 대신 단형 선호 → 안 갈란다
    - 예: 그렇지 않다 → 글찬타
- keywords: ['종결형', '부정법 몬/몯 + 단형 선호 (경북)', '경상도', '문법론']
- 결정: 불확실  (어휘면 제거·조사/어미면 유지 → 확인)

## #39  [GS-00039]  (경어법)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `대구 하소체 특수어미 -습니다`
- **dialect** : `-는구마/-느마`
- explanation: 대구지역에서 하소체 서술형 어미로 특별히 사용. 출처: 경북방언 특징
    - 예: 집에 갑니다. → 집에 가는 구마.
    - 예: 집에 갑니다. → 집에 가느마.
- keywords: ['대구 하소체 특수어미 -는구마/-느마', '경어법', '경상도', '높임표현']
- 결정: 유지  (경어법(존댓말) 유지)

## #40  [GS-00040]  (경어법)
- speech_level: 하라체 | sentence: 평서형 | tense: 현재
- **standard**: `청유형 어미 -자, -으세`
- **dialect** : `청유형 변이 -자, -으시더 / -세`
- explanation: 청유형 종결어미의 지역별 형태. 출처: 경북방언 특징
    - 예: 우리 밥 먹자. → 우리 밥 묵자.
    - 예: 이제 그만 가세. → 인자 고마 가세.
- keywords: ['청유형어미 지역별 변이 (경북)', '경어법', '경상도', '높임표현']
- 결정: 유지  (경어법(존댓말) 유지)

## #41  [GS-00041]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-다 / -어 (친근한 평서형)`
- **dialect** : `-데이`
- explanation: 알려줄 때
    - 예: 내가 갈게. → 내가 간데이.
    - 예: 오늘 비가 와. → 오늘 비 온데이.
- keywords: ['경상도', 'ending', '데이', '~데이', 'gs_ending_001']
- 결정: 유지  (연결어미)

## #42  [GS-00042]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-는대 / -대 (인용 평서형)`
- **dialect** : `-한대이 / -대이`
- explanation: 표준어 '-는대 / -대 (인용 평서형)'에 대응하는 경상 방언 형태소 '-한대이 / -대이' 입니다.
    - 예: 오늘 비가 온대. → 오늘 비 온대이.
    - 예: 그 사람이 공부한대. → 그 사람이 공부한대이.
- keywords: ['경상도', 'ending', '한대이', '~한대이', 'gs_ending_002']
- 결정: 유지  (연결어미)

## #43  [GS-00043]  (연결어미)
- speech_level: 하여체 | sentence: 의문형 | tense: 현재
- **standard**: `-니? / -어? (판정 의문형)`
- **dialect** : `-나?`
- explanation: 표준어 '-니? / -어? (판정 의문형)'에 대응하는 경상 방언 형태소 '-나?' 입니다.
    - 예: 밥 먹었니? → 밥 뭇나?
    - 예: 어디 아프니? → 어데 아프나?
- keywords: ['경상도', 'ending', '나', '~나', 'gs_ending_003']
- 결정: 유지  (연결어미)

## #44  [GS-00044]  (연결어미)
- speech_level: 하여체 | sentence: 의문형 | tense: 현재
- **standard**: `-니? / -어? (설명 의문형)`
- **dialect** : `-노?`
- explanation: 표준어 '-니? / -어? (설명 의문형)'에 대응하는 경상 방언 형태소 '-노?' 입니다.
    - 예: 뭐 먹었니? → 머 뭇노?
    - 예: 어디 가니? → 어데 가노?
- keywords: ['경상도', 'ending', '노', '~노', 'gs_ending_004']
- 결정: 유지  (연결어미)

## #45  [GS-00045]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-습니다`
- **dialect** : `-니더 / -심더`
- explanation: 표준어 '-습니다'에 대응하는 경상 방언 형태소 '-니더 / -심더' 입니다.
    - 예: 아닙니다. → 아입니더.
    - 예: 맞습니다. → 맞습니더.
- keywords: ['경상도', 'ending', '니더', '~니더', 'gs_ending_005']
- 결정: 유지  (연결어미)

## #46  [GS-00046]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-습니다`
- **dialect** : `-심더 / -있심더`
- explanation: 표준어 '-습니다'에 대응하는 경상 방언 형태소 '-심더 / -있심더' 입니다.
    - 예: 없습니다. → 없심더.
    - 예: 그렇습니다. → 그렇심더.
- keywords: ['경상도', 'ending', '심더', '~심더', 'gs_ending_006']
- 결정: 유지  (연결어미)

## #47  [GS-00047]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `합니다 (평서형)`
- **dialect** : `한데이`
- explanation: 해요체→경상 평서
    - 예: 내가 합니다. → 내가 한데이.
- keywords: ['경상도', 'ending', '한데이', '합니다', 'gs_ending_007']
- 결정: 유지  (연결어미)

## #48  [GS-00048]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `해요 (친근한 평서형)`
- **dialect** : `한데이`
- explanation: 표준어 '해요 (친근한 평서형)'에 대응하는 경상 방언 형태소 '한데이' 입니다.
    - 예: 제가 해요. → 내가 한데이.
- keywords: ['경상도', 'ending', '한데이', '해요', 'gs_ending_008']
- 결정: 유지  (연결어미)

## #49  [GS-00049]  (연결어미)
- speech_level: 합서체 | sentence: 의문형 | tense: 현재
- **standard**: `했습니다 / 했잖아요`
- **dialect** : `했다 아인교`
- explanation: 표준어 '했습니다 / 했잖아요'에 대응하는 경상 방언 형태소 '했다 아인교' 입니다.
    - 예: 제가 했습니다. → 내가 했다 아인교.
- keywords: ['경상도', 'ending', '했다 아인교', '했습니다', 'gs_ending_009']
- 결정: 유지  (연결어미)

## #50  [GS-00050]  (연결어미)
- speech_level: 합서체 | sentence: 의문형 | tense: 현재
- **standard**: `했어요 / 했잖아요`
- **dialect** : `했다 아인교`
- explanation: 표준어 '했어요 / 했잖아요'에 대응하는 경상 방언 형태소 '했다 아인교' 입니다.
    - 예: 제가 했어요. → 내가 했다 아인교.
- keywords: ['경상도', 'ending', '했다 아인교', '했어요', 'gs_ending_010']
- 결정: 유지  (연결어미)

## #51  [GS-00051]  (연결어미)
- speech_level: 하라체 | sentence: 평서형 | tense: 현재
- **standard**: `한다 (낮춤 평서형)`
- **dialect** : `한데이`
- explanation: 표준어 '한다 (낮춤 평서형)'에 대응하는 경상 방언 형태소 '한데이' 입니다.
    - 예: 내가 한다. → 내가 한데이.
- keywords: ['경상도', 'ending', '한데이', '한다', 'gs_ending_011']
- 결정: 유지  (연결어미)

## #52  [GS-00052]  (연결어미)
- speech_level: 하라체 | sentence: 평서형 | tense: 현재
- **standard**: `했다고 (간접 인용)`
- **dialect** : `했다꼬`
- explanation: 표준어 '했다고 (간접 인용)'에 대응하는 경상 방언 형태소 '했다꼬' 입니다.
    - 예: 그가 했다고 말했습니다. → 지가 했다꼬 말했십니더.
- keywords: ['경상도', 'ending', '했다꼬', '했다', 'gs_ending_012']
- 결정: 유지  (연결어미)

## #53  [GS-00053]  (연결어미)
- speech_level: 하여체 | sentence: 의문형 | tense: 현재
- **standard**: `하나요? (비격식 의문형)`
- **dialect** : `하는가예?`
- explanation: 표준어 '하나요? (비격식 의문형)'에 대응하는 경상 방언 형태소 '하는가예?' 입니다.
    - 예: 그 일을 하시나요? → 그 일을 하는가예?
- keywords: ['경상도', 'ending', '하는가예', '하나요', 'gs_ending_013']
- 결정: 유지  (연결어미)

## #54  [GS-00054]  (연결어미)
- speech_level: 합서체 | sentence: 의문형 | tense: 현재
- **standard**: `합니까? (격식 의문형)`
- **dialect** : `하는교? / 능교?`
- explanation: 표준어 '합니까? (격식 의문형)'에 대응하는 경상 방언 형태소 '하는교? / 능교?' 입니다.
    - 예: 밥은 먹습니까? → 밥은 뭇는교?
- keywords: ['경상도', 'ending', '하는교', '합니까', 'gs_ending_014']
- 결정: 유지  (연결어미)

## #55  [GS-00055]  (연결어미)
- speech_level: 하여체 | sentence: 의문형 | tense: 현재
- **standard**: `했나요? (과거 의문형)`
- **dialect** : `했는가예?`
- explanation: 표준어 '했나요? (과거 의문형)'에 대응하는 경상 방언 형태소 '했는가예?' 입니다.
    - 예: 어제 학교에 갔나요? → 어제 핵교에 갔는가예?
- keywords: ['경상도', 'ending', '했는가예', '했나요', 'gs_ending_015']
- 결정: 유지  (연결어미)

## #56  [GS-00056]  (연결어미)
- speech_level: 하라체 | sentence: 의문형 | tense: 현재
- **standard**: `하니? (낮춤 의문형)`
- **dialect** : `하나?`
- explanation: 표준어 '하니? (낮춤 의문형)'에 대응하는 경상 방언 형태소 '하나?' 입니다.
    - 예: 지금 공부하니? → 지금 공부하나?
- keywords: ['경상도', 'ending', '하나', '하니', 'gs_ending_016']
- 결정: 유지  (연결어미)

## #57  [GS-00057]  (연결어미)
- speech_level: 하라체 | sentence: 의문형 | tense: 현재
- **standard**: `하니? (설명 의문형 낮춤)`
- **dialect** : `하노?`
- explanation: 표준어 '하니? (설명 의문형 낮춤)'에 대응하는 경상 방언 형태소 '하노?' 입니다.
    - 예: 지금 뭐 하니? → 지금 머 하노?
- keywords: ['경상도', 'ending', '하노', '하노', 'gs_ending_017']
- 결정: 유지  (연결어미)

## #58  [GS-00058]  (연결어미)
- speech_level: 하라체 | sentence: 의문형 | tense: 현재
- **standard**: `했니? (과거 설명 의문형)`
- **dialect** : `했노?`
- explanation: 표준어 '했니? (과거 설명 의문형)'에 대응하는 경상 방언 형태소 '했노?' 입니다.
    - 예: 어제 뭐 했니? → 어제 머 했노?
- keywords: ['경상도', 'ending', '했노', '했노', 'gs_ending_018']
- 결정: 유지  (연결어미)

## #59  [GS-00059]  (연결어미)
- speech_level: 하여체 | sentence: 의문형 | tense: 현재
- **standard**: `그냥 (부사)`
- **dialect** : `고마`
- explanation: 표준어 '그냥 (부사)'에 대응하는 경상 방언 형태소 '고마' 입니다.
    - 예: 그냥 두세요. → 고마 두이소.
- keywords: ['경상도', 'particle', '고마', '그냥', 'gs_ending_019']
- 결정: 유지  (연결어미)

## #60  [GS-00060]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `확실히 / 단단히`
- **dialect** : `단디`
- explanation: 표준어 '확실히 / 단단히'에 대응하는 경상 방언 형태소 '단디' 입니다.
    - 예: 확실히 하세요. → 단디 하이소.
- keywords: ['경상도', 'particle', '단디', '확실히', 'gs_ending_020']
- 결정: 유지  (연결어미)

## #61  [GS-00061]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `합니다 (친근 존대)`
- **dialect** : `합니데이`
- explanation: 표준어 '합니다 (친근 존대)'에 대응하는 경상 방언 형태소 '합니데이' 입니다.
    - 예: 제가 하겠습니다. → 내가 합니데이.
- keywords: ['경상도', 'ending', '합니데이', '합니다', 'gs_ending_00080']
- 결정: 유지  (연결어미)

## #62  [GS-00062]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-습니다`
- **dialect** : `-심더`
- explanation: 표준어 '-습니다'에 대응하는 경상 방언 형태소 '-심더' 입니다.
    - 예: 그렇습니다. → 그렇심더.
- keywords: ['경상도', 'ending', '심더', '습니다', 'gs_ending_00081']
- 결정: 유지  (연결어미)

## #63  [GS-00063]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-해요 (비격식 존대)`
- **dialect** : `-해예`
- explanation: 표준어 '-해요 (비격식 존대)'에 대응하는 경상 방언 형태소 '-해예' 입니다.
    - 예: 그렇게 해요. → 그렇게 해예.
- keywords: ['경상도', 'ending', '해예', '해요', 'gs_ending_00082']
- 결정: 유지  (연결어미)

## #64  [GS-00064]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-하네요 (존대 감탄)`
- **dialect** : `-하네예`
- explanation: 표준어 '-하네요 (존대 감탄)'에 대응하는 경상 방언 형태소 '-하네예' 입니다.
    - 예: 잘 하네요. → 잘 하네예.
- keywords: ['경상도', 'ending', '하네예', '하네요', 'gs_ending_00083']
- 결정: 유지  (연결어미)

## #65  [GS-00065]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `있습니다`
- **dialect** : `있심더`
- explanation: 표준어 '있습니다'에 대응하는 경상 방언 형태소 '있심더' 입니다.
    - 예: 여기 있습니다. → 요기 있심더.
- keywords: ['경상도', 'ending', '있심더', '있습니다', 'gs_ending_00084']
- 결정: 유지  (연결어미)

## #66  [GS-00066]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `죽겠어`
- **dialect** : `죽겠심더`
- explanation: 표준어 '죽겠어'에 대응하는 경상 방언 형태소 '죽겠심더' 입니다.
    - 예: 더워 죽겠어. → 더워 죽겠심더.
- keywords: ['경상도', 'ending', '죽겠심더', '죽겠어', 'gs_ending_00085']
- 결정: 유지  (연결어미)

## #67  [GS-00067]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `미치겠어 / 미치겠네`
- **dialect** : `미치겠심더`
- explanation: 표준어 '미치겠어 / 미치겠네'에 대응하는 경상 방언 형태소 '미치겠심더' 입니다.
    - 예: 답답해 미치겠네. → 답답해 미치겠심더.
- keywords: ['경상도', 'ending', '미치겠심더', '미치겠네', 'gs_ending_00086']
- 결정: 유지  (연결어미)

## #68  [GS-00068]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `모르겠네요`
- **dialect** : `모르겠네예`
- explanation: 표준어 '모르겠네요'에 대응하는 경상 방언 형태소 '모르겠네예' 입니다.
    - 예: 저는 잘 모르겠네요. → 나는 잘 모르겠네예.
- keywords: ['경상도', 'ending', '모르겠네예', '모르겠네', 'gs_ending_00087']
- 결정: 유지  (연결어미)

## #69  [GS-00069]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `그러네요 / 그렇습니다`
- **dialect** : `그렇네예`
- explanation: 표준어 '그러네요 / 그렇습니다'에 대응하는 경상 방언 형태소 '그렇네예' 입니다.
    - 예: 정말 그러네요. → 참말로 그렇네예.
- keywords: ['경상도', 'ending', '그렇네예', '그러네요', 'gs_ending_00088']
- 결정: 유지  (연결어미)

## #70  [GS-00070]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-네요 (어미)`
- **dialect** : `-네예`
- explanation: 표준어 '-네요 (어미)'에 대응하는 경상 방언 형태소 '-네예' 입니다.
    - 예: 예쁘네요. → 이쁘네예.
- keywords: ['경상도', 'ending', '네예', '네요', 'gs_ending_00089']
- 결정: 유지  (연결어미)

## #71  [GS-00071]  (연결어미)
- speech_level: 하여체 | sentence: 의문형 | tense: 현재
- **standard**: `은가요`
- **dialect** : `는가예`
- explanation: 표준어 '은가요'에 대응하는 경상 방언 형태소 '는가예' 입니다.
- keywords: ['경상도', 'ending', '는가예', '은가요', 'gs_ending_00090']
- 결정: 유지  (연결어미)

## #72  [GS-00072]  (연결어미)
- speech_level: 하여체 | sentence: 의문형 | tense: 현재
- **standard**: `-는가요?`
- **dialect** : `-는가예?`
- explanation: 표준어 '-는가요?'에 대응하는 경상 방언 형태소 '-는가예?' 입니다.
    - 예: 가는가요? → 가는가예?
- keywords: ['경상도', 'ending', '는가예', '는가요', 'gs_ending_00091']
- 결정: 유지  (연결어미)

## #73  [GS-00073]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `네 (대답)`
- **dialect** : `예`
- explanation: 표준어 '네 (대답)'에 대응하는 경상 방언 형태소 '예' 입니다.
    - 예: 네, 알겠습니다. → 예, 알겠심더.
- keywords: ['경상도', 'ending', '예', '네', 'gs_ending_00092']
- 결정: 유지  (연결어미)

## #74  [GS-00074]  (연결어미)
- speech_level: 하여체 | sentence: 의문형 | tense: 현재
- **standard**: `아유 (감탄사)`
- **dialect** : `아이고 / 에헤이`
- explanation: 표준어 '아유 (감탄사)'에 대응하는 경상 방언 형태소 '아이고 / 에헤이' 입니다.
    - 예: 아유, 힘들어. → 아이고, 힘들어라.
- keywords: ['경상도', 'ending', '아이고', '아유', 'gs_ending_00093']
- 결정: 유지  (연결어미)

## #75  [GS-00075]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `정말 / 진짜로`
- **dialect** : `억수로 / 참말로`
- explanation: 표준어 '정말 / 진짜로'에 대응하는 경상 방언 형태소 '억수로 / 참말로' 입니다.
    - 예: 참말로 많다. → 억수로 많다.
- keywords: ['경상도', 'ending', '억수로', '참말로', 'gs_ending_00094']
- 결정: 유지  (연결어미)

## #76  [GS-00076]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `매우 / 아주 / 정말`
- **dialect** : `억수로 / 항거시`
- explanation: 표준어 '매우 / 아주 / 정말'에 대응하는 경상 방언 형태소 '억수로 / 항거시' 입니다.
    - 예: 정말 덥다. → 억수로 덥다.
- keywords: ['경상도', 'ending', '억수로', '정말', 'gs_ending_00095']
- 결정: 유지  (연결어미)

## #77  [GS-00077]  (연결어미)
- speech_level: 하여체 | sentence: 의문형 | tense: 현재
- **standard**: `-니? / -냐? (판정 의문형)`
- **dialect** : `-나?`
- explanation: 관련 문답
    - 예: 밥 먹었니? → 밥 뭇나?
- keywords: ['경상도', 'ending', '나', '-나', 'gs_ending_00096']
- 결정: 유지  (연결어미)

## #78  [GS-00078]  (연결어미)
- speech_level: 하여체 | sentence: 의문형 | tense: 현재
- **standard**: `-니? / -냐? (설명 의문형)`
- **dialect** : `-노?`
- explanation: 관련 문답
    - 예: 어디 가니? → 어데 가노?
- keywords: ['경상도', 'ending', '노', '-노', 'gs_ending_00097']
- 결정: 유지  (연결어미)

## #79  [GS-00079]  (연결어미)
- speech_level: 하여체 | sentence: 의문형 | tense: 현재
- **standard**: `-이니? (체언 뒤 판정 의문)`
- **dialect** : `-(이)가?`
- explanation: 관련 문답
    - 예: 너 학생이니? → 니 학생이가?
- keywords: ['경상도', 'ending', '가', '-가', 'gs_ending_00098']
- 결정: 유지  (연결어미)

## #80  [GS-00080]  (연결어미)
- speech_level: 하여체 | sentence: 의문형 | tense: 현재
- **standard**: `-이니? (체언 뒤 설명 의문)`
- **dialect** : `-(이)고?`
- explanation: 관련 문답
    - 예: 이게 뭐니? → 이게 뭐고?
- keywords: ['경상도', 'ending', '고', '-고', 'gs_ending_00099']
- 결정: 유지  (연결어미)

## #81  [GS-00081]  (연결어미)
- speech_level: 하라체 | sentence: 평서형 | tense: 현재
- **standard**: `-는가 / -나 (의문형)`
- **dialect** : `-누`
- explanation: 관련 문답
    - 예: 자네 지금 어디 가는가? → 자네 지금 어데 가누?
- keywords: ['경상도', 'ending', '누', '-누', 'gs_ending_00100']
- 결정: 유지  (연결어미)

## #82  [GS-00082]  (연결어미)
- speech_level: 합서체 | sentence: 의문형 | tense: 현재
- **standard**: `-소? / -오? (의문형)`
- **dialect** : `-노형?`
- explanation: 관련 문답
    - 예: 어디 가오? → 어데 가노형?
- keywords: ['경상도', 'ending', '노형', '-노형', 'gs_ending_00101']
- 결정: 유지  (연결어미)

## #83  [GS-00083]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-하오체 어미`
- **dialect** : `-하소체 어미`
- explanation: 관련 문답
    - 예: 이리 오시오. → 이리 오소.
- keywords: ['경상도', 'ending', '하소체', '-하소체', 'gs_ending_00102']
- 결정: 유지  (연결어미)

## #84  [GS-00084]  (연결어미)
- speech_level: 합서체 | sentence: 의문형 | tense: 현재
- **standard**: `-는가요? (하오체)`
- **dialect** : `-는교?`
- explanation: 관련 문답
    - 예: 벌써 가시나요? → 벌써 가시는교?
- keywords: ['경상도', 'ending', '능교', '-능교', 'gs_ending_00103']
- 결정: 유지  (연결어미)

## #85  [GS-00085]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-십니까? (북부 경어법)`
- **dialect** : `-니껴?`
- explanation: 관련 문답
    - 예: 벌써 가시나요? → 벌써 가시니껴?
- keywords: ['경상도', 'ending', '니껴', '-니껴', 'gs_ending_00104']
- 결정: 유지  (연결어미)

## #86  [GS-00086]  (연결어미)
- speech_level: 합서체 | sentence: 명령형 | tense: 현재
- **standard**: `-하십시오 (최상위 높임)`
- **dialect** : `-하이소 / -으이소`
- explanation: 관련 문답
    - 예: 어서 오십시오. → 어서 오이소.
- keywords: ['경상도', 'ending', '하이소', '-하이소', 'gs_ending_00105']
- 결정: 유지  (연결어미)

## #87  [GS-00087]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-합니다 (경식 높임)`
- **dialect** : `-합니더`
- explanation: 관련 문답
    - 예: 제가 하겠습니다. → 내가 합니더.
- keywords: ['경상도', 'ending', '합니더', '-합니더', 'gs_ending_00106']
- 결정: 유지  (연결어미)

## #88  [GS-00088]  (연결어미)
- speech_level: 합서체 | sentence: 의문형 | tense: 현재
- **standard**: `-합니까? (격식 높임 의문)`
- **dialect** : `-합니꺼?`
- explanation: 관련 문답
    - 예: 언제 출발합니까? → 언제 출발합니꺼?
- keywords: ['경상도', 'ending', '합니꺼', '-합니꺼', 'gs_ending_00107']
- 결정: 유지  (연결어미)

## #89  [GS-00089]  (연결어미)
- speech_level: 합서체 | sentence: 의문형 | tense: 현재
- **standard**: `-하는가요? (하오체)`
- **dialect** : `-하능교?`
- explanation: 관련 문답
    - 예: 지금 식사하시는가요? → 지금 식사하능교?
- keywords: ['경상도', 'ending', '하능교', '-하능교', 'gs_ending_00108']
- 결정: 유지  (연결어미)

## #90  [GS-00090]  (연결어미)
- speech_level: 합서체 | sentence: 의문형 | tense: 현재
- **standard**: `-는가요? / -나요?`
- **dialect** : `-는교? / 능교?`
- explanation: 관련 문답
    - 예: 밥은 먹습니까? → 밥은 뭇는교?
- keywords: ['경상도', 'ending', '는교', '-는교', 'gs_ending_00109']
- 결정: 유지  (연결어미)

## #91  [GS-00091]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-요 (비격식 존대)`
- **dialect** : `-예`
- explanation: 실존 인물
    - 예: 네, 그렇습니다. → 예, 그렇습니더예.
- keywords: ['경상도', 'ending', '예', '~예', 'gs_ending_00110']
- 결정: 유지  (연결어미)

## #92  [GS-00092]  (연결어미)
- speech_level: 합서체 | sentence: 명령형 | tense: 현재
- **standard**: `-십시오 (정중 명령)`
- **dialect** : `-이소 / -으이소`
- explanation: 실존 인물
    - 예: 이리 오십시오. → 이리 오이소.
- keywords: ['경상도', 'ending', '이소', '~이소', 'gs_ending_00111']
- 결정: 유지  (연결어미)

## #93  [GS-00093]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-시- (높임 선어말어미)`
- **dialect** : `-시-`
- explanation: 의문의 종결 표지 '-나', '-노', '~(이)가', '~(이)고'
    - 예: 어디 가시나요? → 어데 가시노?
    - 예: 밥 드셨습니까? → 밥 뭇싯나?
- keywords: ['경상도', 'ending', '시', '-시', 'gs_ending_00112']
- 결정: 유지  (연결어미)

## #94  [GS-00094]  (연결어미)
- speech_level: 하라체 | sentence: 평서형 | tense: 현재
- **standard**: `-라고 하다 (간접 인용)`
- **dialect** : `-라카다`
- explanation: 대구
    - 예: 철수가 가라고 한다. → 철수가 가라칸다.
- keywords: ['경상도', 'ending', '라카다', '-라카다', 'gs_ending_00113']
- 결정: 유지  (연결어미)

## #95  [GS-00095]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-다 / -어 (친근한 평서형)`
- **dialect** : `-대이`
- explanation: 대구
    - 예: 내가 먼저 갈게. → 내 먼저 간대이.
- keywords: ['경상도', 'ending', '대이', '-대이', 'gs_ending_00114']
- 결정: 유지  (연결어미)

## #96  [GS-00096]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-요 / -오 (존대 평서)`
- **dialect** : `-우 / -웋`
- explanation: 대구
    - 예: 빨리 와요. → 퍼뜩 오우.
- keywords: ['경상도', 'ending', '웋', '-웋', 'gs_ending_00115']
- 결정: 유지  (연결어미)

## #97  [GS-00097]  (연결어미)
- speech_level: 하라체 | sentence: 평서형 | tense: 현재
- **standard**: `-이다 (서술 격틀)`
- **dialect** : `-이라 / -이다`
- explanation: 대구
    - 예: 이건 책이다. → 이건 책이라.
- keywords: ['경상도', 'ending', '이다', '-이다', 'gs_ending_00116']
- 결정: 유지  (연결어미)

## #98  [GS-00098]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-이었습니다 (과거 평서)`
- **dialect** : `-이랐십니더`
- explanation: 대구
    - 예: 그는 군인이었습니다. → 지는 군인이랐십니더.
- keywords: ['경상도', 'ending', '이랐습니다', '-이랐습니다', 'gs_ending_00117']
- 결정: 유지  (연결어미)

## #99  [GS-00099]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-이야 (반말 서술)`
- **dialect** : `-이라 / -이다`
- explanation: 대구
    - 예: 그건 내 책이야. → 그건 내 책이라.
- keywords: ['경상도', 'ending', '이야', '-이야', 'gs_ending_00118']
- 결정: 유지  (연결어미)

## #100  [GS-00100]  (연결어미)
- speech_level: 하라체 | sentence: 평서형 | tense: 현재
- **standard**: `-이다 (어미 서술)`
- **dialect** : `-이라`
- explanation: 대구
    - 예: 이건 내 책이다. → 이건 내 책이라.
- keywords: ['경상도', 'ending', '이라', '-이라', 'gs_ending_00119']
- 결정: 유지  (연결어미)

## #101  [GS-00101]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-대다 (반복 보조동사)`
- **dialect** : `-대다`
- explanation: 동남 방언 단어
    - 예: 아이들이 떠들어댄다. → 아들이 씨부려댄다.
- keywords: ['경상도', 'ending', '대다', '-대다', 'gs_ending_00120']
- 결정: 유지  (연결어미)

## #102  [GS-00102]  (연결어미)
- speech_level: 하라체 | sentence: 평서형 | tense: 현재
- **standard**: `-뜨리다 / -버리다 (보조용언)`
- **dialect** : `-지기다 / -지끼다`
- explanation: 동남 방언 단어
    - 예: 그릇을 깨뜨려 버렸다. → 그릇을 깨지기뿠다.
- keywords: ['경상도', 'ending', '지기다', '-지기다', 'gs_ending_00121']
- 결정: 유지  (연결어미)

## #103  [GS-00103]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-기 (명사형 전성어미)`
- **dialect** : `-기`
- explanation: 동남 방언 단어
    - 예: 밥 먹기가 싫다. → 밥 묵기가 실타.
- keywords: ['경상도', 'ending', '기', '-기', 'gs_ending_00122']
- 결정: 유지  (연결어미)

## #104  [GS-00104]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `-게 (부사형 전성어미)`
- **dialect** : `-게`
- explanation: 동남 방언 단어
    - 예: 예쁘게 칠해라. → 이쁘게 칠해라.
- keywords: ['경상도', 'ending', '게', '-게', 'gs_ending_00123']
- 결정: 유지  (연결어미)

## #105  [GS-00105]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-습니다 / -다 (평서형)`
- **dialect** : `-니더 / -다`
- explanation: 하이소체
    - 예: 그렇습니다. → 그렇다.
- keywords: ['경상도', 'ending', '다', '-다', 'gs_ending_00124']
- 결정: 유지  (연결어미)

## #106  [GS-00106]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-더군요 (회상 어미)`
- **dialect** : `-디더 / -더`
- explanation: 하이소체
    - 예: 비가 오더군요. → 비가 오디더.
- keywords: ['경상도', 'ending', '더', '-더', 'gs_ending_00125']
- 결정: 유지  (연결어미)

## #107  [GS-00107]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-습니까? (의문형)`
- **dialect** : `-니꺼? / -까?`
- explanation: 하이소체
    - 예: 오늘 비가 옵니까? → 오늘 비가 옵니꺼?
- keywords: ['경상도', 'ending', '까', '-까', 'gs_ending_00126']
- 결정: 유지  (연결어미)

## #108  [GS-00108]  (연결어미)
- speech_level: 하여체 | sentence: 의문형 | tense: 현재
- **standard**: `-까? (의문)`
- **dialect** : `-꺼?`
- explanation: 하이소체
    - 예: 어디 갈까? → 어데 갈꺼?
- keywords: ['경상도', 'ending', '꺼', '-꺼', 'gs_ending_00127']
- 결정: 유지  (연결어미)

## #109  [GS-00109]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-하십시오 / -읍시다 (존대 명령/청유)`
- **dialect** : `-시더 / -셔`
- explanation: 하이소체
    - 예: 이리 오십시오. → 이리 오셔.
- keywords: ['경상도', 'ending', '셔', '-셔', 'gs_ending_00128']
- 결정: 유지  (연결어미)

## #110  [GS-00110]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-습니다 (존대 평서)`
- **dialect** : `-니더`
- explanation: 니껴형 어미
    - 예: 맞습니다. → 맞니더.
- keywords: ['경상도', 'ending', '니더', '-니더', 'gs_ending_00129']
- 결정: 유지  (연결어미)

## #111  [GS-00111]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-습니다 (정중 존대 평서)`
- **dialect** : `-니이더`
- explanation: 니껴형 어미
    - 예: 그렇게 하겠습니다. → 그렇게 하니이더.
- keywords: ['경상도', 'ending', '니이더', '-니이더', 'gs_ending_00130']
- 결정: 유지  (연결어미)

## #112  [GS-00112]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-겠습니다 (의지/추측)`
- **dialect** : `-겠니껴 / -겠니꺼`
- explanation: 니껴형 어미
    - 예: 제가 하겠습니다. → 내가 하겠니껴.
- keywords: ['경상도', 'ending', '겠습니다', '-겠습니다', 'gs_ending_00131']
- 결정: 유지  (연결어미)

## #113  [GS-00113]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-더냐? / -던가요? (회상 의문)`
- **dialect** : `-디껴? / -디?`
- explanation: 니껴형 어미
    - 예: 철수가 밥을 먹던가요? → 철수가 밥 묵디껴?
- keywords: ['경상도', 'ending', '디', '-디', 'gs_ending_00132']
- 결정: 유지  (연결어미)

## #114  [GS-00114]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-더군요 (과거 평서)`
- **dialect** : `-디더`
- explanation: 니껴형 어미
    - 예: 그 사람이 열심히 일하더군요. → 그 사람이 열심히 일하디더.
- keywords: ['경상도', 'ending', '디더', '-디더', 'gs_ending_00133']
- 결정: 유지  (연결어미)

## #115  [GS-00115]  (연결어미)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `-던가요? (과거 의문)`
- **dialect** : `-디껴?`
- explanation: 니껴형 어미
    - 예: 그 사람이 집에 오던가요? → 그 사람이 집에 오디껴?
- keywords: ['경상도', 'ending', '디껴', '-디껴', 'gs_ending_00134']
- 결정: 유지  (연결어미)

## #116  [GS-00116]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `들어가다 (동사)`
- **dialect** : `드가다`
- explanation: 표준어 '들어가다 (동사)'에 대응하는 경상 방언 형태소 '드가다' 입니다.
    - 예: 들어가다 → 드가다
- keywords: ['경상도', 'ending', '들어', '드가다', 'gs_ending_00135']
- 결정: 유지  (연결어미)

## #117  [GS-00117]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `들어오다 (동사)`
- **dialect** : `들오다`
- explanation: 표준어 '들어오다 (동사)'에 대응하는 경상 방언 형태소 '들오다' 입니다.
    - 예: 들어오다 → 들오다
- keywords: ['경상도', 'ending', '들어', '들오다', 'gs_ending_00136']
- 결정: 유지  (연결어미)

## #118  [GS-00118]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `두들겨 맞다 (동사)`
- **dialect** : `뚜드리맞다`
- explanation: 표준어 '두들겨 맞다 (동사)'에 대응하는 경상 방언 형태소 '뚜드리맞다' 입니다.
    - 예: 흠씬 맞다 → 흠씬 뚜드리맞다
- keywords: ['경상도', 'ending', '뚜드리', '맞다', 'gs_ending_00137']
- 결정: 유지  (연결어미)

## #119  [GS-00119]  (연결어미)
- speech_level: 하라체 | sentence: 평서형 | tense: 현재
- **standard**: `내버리다 (동사)`
- **dialect** : `내삐다 / 내삐리다`
- explanation: 표준어 '내버리다 (동사)'에 대응하는 경상 방언 형태소 '내삐다 / 내삐리다' 입니다.
    - 예: 내버려라. → 내삐려라.
- keywords: ['경상도', 'ending', '내버리다', '내삐다', 'gs_ending_00138']
- 결정: 유지  (연결어미)

## #120  [GS-00120]  (연결어미)
- speech_level: 하라체 | sentence: 평서형 | tense: 현재
- **standard**: `일어나다 (동사)`
- **dialect** : `인나라 / 일나라`
- explanation: 표준어 '일어나다 (동사)'에 대응하는 경상 방언 형태소 '인나라 / 일나라' 입니다.
    - 예: 일어나라. → 인나라.
- keywords: ['경상도', 'ending', '일어', '인나다', 'gs_ending_00139']
- 결정: 유지  (연결어미)

## #121  [GS-00121]  (연결어미)
- speech_level: 하여체 | sentence: 의문형 | tense: 현재
- **standard**: `좋지`
- **dialect** : `나야`
- explanation: 표준어 '좋지'에 대응하는 경상 방언 형태소 '나야' 입니다.
- keywords: ['경상도', 'ending', '나야', '좋지', 'gs_ending_00140']
- 결정: 유지  (연결어미)

## #122  [GS-00122]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `개발하다`
- **dialect** : `물질하다`
- explanation: 표준어 '개발하다'에 대응하는 경상 방언 형태소 '물질하다' 입니다.
- keywords: ['경상도', 'ending', '물질하다', '개발하다', 'gs_ending_00141']
- 결정: 유지  (연결어미)

## #123  [GS-00123]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `코딱지 (명사)`
- **dialect** : `코따까리 / 따까리`
- explanation: 표준어 '코딱지 (명사)'에 대응하는 경상 방언 형태소 '코따까리 / 따까리' 입니다.
    - 예: 딱지가 붙었다. → 따까리가 붙었다.
- keywords: ['경상도', 'ending', '코따까리', '딱지', 'gs_ending_00142']
- 결정: 유지  (연결어미)

## #124  [GS-00124]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `우세`
- **dialect** : `그러다`
- explanation: 표준어 '우세'에 대응하는 경상 방언 형태소 '그러다' 입니다.
- keywords: ['경상도', 'phonology', '그러다', '우세', 'gs_ending_00143']
- 결정: 유지  (연결어미)

## #125  [GS-00125]  (연결어미)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `전역`
- **dialect** : `그러다`
- explanation: 표준어 '전역'에 대응하는 경상 방언 형태소 '그러다' 입니다.
- keywords: ['경상도', 'phonology', '그러다', '전역', 'gs_ending_00144']
- 결정: 유지  (연결어미)

## #126  [GS-00126]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `어떡해`
- **dialect** : `우야꼬`
- explanation: 표준어 관용구 '어떡해' 대신 방언 관용구 '우야꼬'를 사용합니다.
    - 예: 어쿠 이 일을 어떡해... → 아따마 이 일을 우야꼬...
- keywords: ['경상도', '관용구', '우야꼬', '어떡해', 'gs_phrase_001']
- 결정: 제거  (어휘/표현(문법 아님))

## #127  [GS-00127]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `매우 많이`
- **dialect** : `천지삐까리`
- explanation: 표준어 관용구 '매우 많이' 대신 방언 관용구 '천지삐까리'를 사용합니다.
    - 예: 길가에 쓰레기가 아주 많이 널렸어요 → 길가에 쓰레기가 천지삐까리데이
- keywords: ['경상도', '관용구', '천지삐까리', '매우 많이', 'gs_phrase_002']
- 결정: 제거  (어휘/표현(문법 아님))

## #128  [GS-00128]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `그렇지?`
- **dialect** : `맞다 아이가`
- explanation: 표준어 관용구 '그렇지?' 대신 방언 관용구 '맞다 아이가'를 사용합니다.
    - 예: 오늘 날씨 참 덥지 그렇지? → 오늘 날씨 참 덥다 아이가
- keywords: ['경상도', '관용구', '맞다 아이가', '그렇지?', 'gs_phrase_003']
- 결정: 제거  (어휘/표현(문법 아님))

## #129  [GS-00129]  (구절/관용구)
- speech_level: 합서체 | sentence: 평서형 | tense: 현재
- **standard**: `확실히 해 주세요`
- **dialect** : `단디 해 주이소`
- explanation: 표준어 관용구 '확실히 해 주세요' 대신 방언 관용구 '단디 해 주이소'를 사용합니다.
- keywords: ['경상도', '관용구', '단디 해 주이소', '확실히 해 주세요', 'phrase_001']
- 결정: 제거  (어휘/표현(문법 아님))

## #130  [GS-00137]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `영`
- **dialect** : `주`
- explanation: 표준어 관용구 '영' 대신 방언 관용구 '주'를 사용합니다.
- keywords: ['경상', 'phonology_lexeme', '주', '영', 'gs_phrase_00065']
- 결정: 제거  (어휘/표현(문법 아님))

## #131  [GS-00138]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `형님`
- **dialect** : `헹님`
- explanation: 표준어 관용구 '형님' 대신 방언 관용구 '헹님'를 사용합니다.
- keywords: ['경상', 'phonology_lexeme', '헹님', '형님', 'gs_phrase_00066']
- 결정: 제거  (어휘/표현(문법 아님))

## #132  [GS-00139]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `헤임`
- **dialect** : `헴`
- explanation: 표준어 관용구 '헤임' 대신 방언 관용구 '헴'를 사용합니다.
- keywords: ['경상', 'phonology_lexeme', '헴', '헤임', 'gs_phrase_00067']
- 결정: 제거  (어휘/표현(문법 아님))

## #133  [GS-00140]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `선새임`
- **dialect** : `새임`
- explanation: 표준어 관용구 '선새임' 대신 방언 관용구 '새임'를 사용합니다.
- keywords: ['경상', 'phonology_lexeme', '새임', '선새임', 'gs_phrase_00068']
- 결정: 제거  (어휘/표현(문법 아님))

## #134  [GS-00141]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `스새님`
- **dialect** : `스앤님`
- explanation: 표준어 관용구 '스새님' 대신 방언 관용구 '스앤님'를 사용합니다.
- keywords: ['경상', 'phonology_lexeme', '스앤님', '스새님', 'gs_phrase_00069']
- 결정: 제거  (어휘/표현(문법 아님))

## #135  [GS-00142]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `아이`
- **dialect** : `그`
- explanation: 표준어 관용구 '아이' 대신 방언 관용구 '그'를 사용합니다.
- keywords: ['경상', 'phonology_lexeme', '그', '아이', 'gs_phrase_00070']
- 결정: 제거  (어휘/표현(문법 아님))

## #136  [GS-00143]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `그 아이 (대명사)`
- **dialect** : `가 / 가가`
- explanation: 표준어 관용구 '그 아이 (대명사)' 대신 방언 관용구 '가 / 가가'를 사용합니다.
    - 예: 그 아이가 그 아이니? → 가가 가가?
- keywords: ['경상', 'phonology_lexeme', '가', '아', 'gs_phrase_00071']
- 결정: 제거  (어휘/표현(문법 아님))

## #137  [GS-00144]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `오늘 (명사/부사)`
- **dialect** : `올 / 오늘`
- explanation: 표준어 관용구 '오늘 (명사/부사)' 대신 방언 관용구 '올 / 오늘'를 사용합니다.
    - 예: 오늘 갈게. → 올 간데이.
- keywords: ['경상', 'phonology_lexeme', '올', '오늘', 'gs_phrase_00072']
- 결정: 제거  (어휘/표현(문법 아님))

## #138  [GS-00145]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `지금 (명사/부사)`
- **dialect** : `짐 / 지끔`
- explanation: 표준어 관용구 '지금 (명사/부사)' 대신 방언 관용구 '짐 / 지끔'를 사용합니다.
    - 예: 지금 뭐 해? → 짐 머 하노?
- keywords: ['경상', 'phonology_lexeme', '짐', '지금', 'gs_phrase_00073']
- 결정: 제거  (어휘/표현(문법 아님))

## #139  [GS-00146]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `내일 (명사/부사)`
- **dialect** : `낼 / 내일`
- explanation: 표준어 관용구 '내일 (명사/부사)' 대신 방언 관용구 '낼 / 내일'를 사용합니다.
    - 예: 내일 만나자. → 낼 만나재이.
- keywords: ['경상', 'phonology_lexeme', '낼', '내일', 'gs_phrase_00074']
- 결정: 제거  (어휘/표현(문법 아님))

## #140  [GS-00147]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `외무`
- **dialect** : `애무`
- explanation: 표준어 관용구 '외무' 대신 방언 관용구 '애무'를 사용합니다.
- keywords: ['경상', 'phonology_lexeme', '애무', '외무', 'gs_phrase_00075']
- 결정: 제거  (어휘/표현(문법 아님))

## #141  [GS-00148]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `류현진 (고유명사)`
- **dialect** : `루현진`
- explanation: 표준어 관용구 '류현진 (고유명사)' 대신 방언 관용구 '루현진'를 사용합니다.
    - 예: 류현진 선수가 등판한다. → 루현진 선수가 등판한다.
- keywords: ['경상', 'phonology_lexeme', '루', '류현진', 'gs_phrase_00076']
- 결정: 제거  (어휘/표현(문법 아님))

## #142  [GS-00149]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `김광현`
- **dialect** : `김`
- explanation: 표준어 관용구 '김광현' 대신 방언 관용구 '김'를 사용합니다.
- keywords: ['경상', 'phonology_lexeme', '김', '김광현', 'gs_phrase_00077']
- 결정: 제거  (어휘/표현(문법 아님))

## #143  [GS-00150]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `의사 (명사)`
- **dialect** : `으사`
- explanation: 표준어 관용구 '의사 (명사)' 대신 방언 관용구 '으사'를 사용합니다.
    - 예: 의사 선생님이 오신다. → 으사 선생님이 오신다.
- keywords: ['경상', 'phonology_lexeme', '으사', '의사', 'gs_phrase_00078']
- 결정: 제거  (어휘/표현(문법 아님))

## #144  [GS-00151]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `고기 (명사)`
- **dialect** : `괴기`
- explanation: 표준어 관용구 '고기 (명사)' 대신 방언 관용구 '괴기'를 사용합니다.
    - 예: 소고기 먹자. → 소괴기 묵자.
- keywords: ['경상', 'phonology_lexeme', '괴기', '고기', 'gs_phrase_00079']
- 결정: 제거  (어휘/표현(문법 아님))

## #145  [GS-00152]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `학교 (명사)`
- **dialect** : `핵교`
- explanation: 표준어 관용구 '학교 (명사)' 대신 방언 관용구 '핵교'를 사용합니다.
    - 예: 학교에 가자. → 핵교에 가재이.
- keywords: ['경상', 'phonology_lexeme', '핵교', '학교', 'gs_phrase_00080']
- 결정: 제거  (어휘/표현(문법 아님))

## #146  [GS-00153]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `경상도 (고유명사)`
- **dialect** : `겡상도`
- explanation: 표준어 관용구 '경상도 (고유명사)' 대신 방언 관용구 '겡상도'를 사용합니다.
    - 예: 경상도 사람입니다. → 겡상도 사람입니더.
- keywords: ['경상', 'phonology_lexeme', '겡상도', '경상도', 'gs_phrase_00081']
- 결정: 제거  (어휘/표현(문법 아님))

## #147  [GS-00154]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `경주 (고유명사)`
- **dialect** : `겡주`
- explanation: 표준어 관용구 '경주 (고유명사)' 대신 방언 관용구 '겡주'를 사용합니다.
    - 예: 경주에 산다. → 겡주에 산다.
- keywords: ['경상', 'phonology_lexeme', '겡주', '경주', 'gs_phrase_00082']
- 결정: 제거  (어휘/표현(문법 아님))

## #148  [GS-00155]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `명문`
- **dialect** : `멩문`
- explanation: 표준어 관용구 '명문' 대신 방언 관용구 '멩문'를 사용합니다.
- keywords: ['경상', 'phonology_lexeme', '멩문', '명문', 'gs_phrase_00083']
- 결정: 제거  (어휘/표현(문법 아님))

## #149  [GS-00156]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `경제`
- **dialect** : `겡제`
- explanation: 표준어 관용구 '경제' 대신 방언 관용구 '겡제'를 사용합니다.
- keywords: ['경상', 'phonology_lexeme', '겡제', '경제', 'gs_phrase_00084']
- 결정: 제거  (어휘/표현(문법 아님))

## #150  [GS-00157]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `변별력`
- **dialect** : `벤벨렉`
- explanation: 표준어 관용구 '변별력' 대신 방언 관용구 '벤벨렉'를 사용합니다.
- keywords: ['경상', 'phonology_lexeme', '벤벨렉', '변별력', 'gs_phrase_00085']
- 결정: 제거  (어휘/표현(문법 아님))

## #151  [GS-00158]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `현대 (명사)`
- **dialect** : `헨대`
- explanation: 표준어 관용구 '현대 (명사)' 대신 방언 관용구 '헨대'를 사용합니다.
    - 예: 현대 자동차 → 헨대 자동차
- keywords: ['경상', 'phonology_lexeme', '헨대', '현대', 'gs_phrase_00086']
- 결정: 제거  (어휘/표현(문법 아님))

## #152  [GS-00159]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `별로 (부사)`
- **dialect** : `벨로`
- explanation: 표준어 관용구 '별로 (부사)' 대신 방언 관용구 '벨로'를 사용합니다.
    - 예: 별로 맛없다. → 벨로 맛없다.
- keywords: ['경상', 'phonology_lexeme', '벨로', '별로', 'gs_phrase_00087']
- 결정: 제거  (어휘/표현(문법 아님))

## #153  [GS-00160]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `영주`
- **dialect** : `이엉주`
- explanation: 표준어 관용구 '영주' 대신 방언 관용구 '이엉주'를 사용합니다.
- keywords: ['경상', 'phonology_lexeme', '이엉주', '영주', 'gs_phrase_00088']
- 결정: 제거  (어휘/표현(문법 아님))

## #154  [GS-00161]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `명순이`
- **dialect** : `멩수이`
- explanation: 표준어 관용구 '명순이' 대신 방언 관용구 '멩수이'를 사용합니다.
- keywords: ['경상', 'phonology_lexeme', '멩수이', '명순이', 'gs_phrase_00089']
- 결정: 제거  (어휘/표현(문법 아님))

## #155  [GS-00162]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `아니, 그게 아니고 (감탄사/구문)`
- **dialect** : `아니, 그기 아니고`
- explanation: 표준어 관용구 '아니, 그게 아니고 (감탄사/구문)' 대신 방언 관용구 '아니, 그기 아니고'를 사용합니다.
    - 예: 아니, 그게 아니고 → 아니, 그기 아니고
- keywords: ['경상', 'phonology_lexeme', '그기', '아이고', 'gs_phrase_00090']
- 결정: 제거  (어휘/표현(문법 아님))

## #156  [GS-00163]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `그것이 아니고 (구문)`
- **dialect** : `그기 아니고 / 그기 아인고`
- explanation: 표준어 관용구 '그것이 아니고 (구문)' 대신 방언 관용구 '그기 아니고 / 그기 아인고'를 사용합니다.
    - 예: 그것이 아니고 → 그기 아니고
- keywords: ['경상', 'phonology_lexeme', '그게', '아니고', 'gs_phrase_00091']
- 결정: 제거  (어휘/표현(문법 아님))

## #157  [GS-00174]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `북동부`
- **dialect** : `어찌`
- explanation: 표준어 관용구 '북동부' 대신 방언 관용구 '어찌'를 사용합니다.
- keywords: ['경상', 'phonology_lexeme', '어찌', '북동부', 'gs_phrase_00102']
- 결정: 제거  (어휘/표현(문법 아님))

## #158  [GS-00175]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `우세`
- **dialect** : `어찌`
- explanation: 표준어 관용구 '우세' 대신 방언 관용구 '어찌'를 사용합니다.
- keywords: ['경상', 'phonology_lexeme', '어찌', '우세', 'gs_phrase_00103']
- 결정: 제거  (어휘/표현(문법 아님))

## #159  [GS-00176]  (구절/관용구)
- speech_level: 하여체 | sentence: 평서형 | tense: 현재
- **standard**: `전역`
- **dialect** : `그`
- explanation: 표준어 관용구 '전역' 대신 방언 관용구 '그'를 사용합니다.
- keywords: ['경상', 'phonology_lexeme', '그', '전역', 'gs_phrase_00104']
- 결정: 제거  (어휘/표현(문법 아님))
