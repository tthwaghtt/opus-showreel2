# HX-01 KESTREL — 빌드 규칙 (CONTRACT, v2)

> 코드를 쓰기 전에 읽는 규칙서. 무엇을 만드는지는 `PLAN.md`, 3D 제작 방법은 `BLENDER_METHOD.md`,
> 공학 숫자는 `calc/specs.json`(원본 `calc/specs.py`), 부품 개수·외형 치수는 모델 매니페스트가 기준이다.
> 문서끼리 충돌하면 숫자는 계산 시트·매니페스트, 내용은 PLAN.md가 우선한다.
> 작업 방식: **단일 에이전트** (서브에이전트 사용 안 함).
> v2 (2026-09-30): 전신 장갑형, 비행 없음, 수소 연료전지. v1 규칙 중 터빈·연료·비행 관련은 모두 삭제했다.

## 1. 파일 구조 (Vite 프로젝트, 레퍼런스 OPUS MECHANICA 구조를 기법으로 계승 — PLAN 12절)
```
calc/specs.py            계산 시트 v2 (실행하면 calc/specs.json 생성, 설계 규칙 검사)
calc/specs.json          모든 공학 수치의 단일 원본 (웹은 Vite로 직접 import)
index.html               모든 DOM (로더, 표제란, HUD, 시트 라벨, 폼, 자유 관람 패널)
src/main.js              부트스트랩: 로더 → World 빌드 → Lenis/ScrollTrigger → 렌더 루프
src/core/                core.js(KX: specs·매니페스트 접근, 스프링), math.js(seg/windowed/damp…), quality.js(품질 등급)
src/world/               three.js: world, environment(격납고 PMREM), materials(patchFx, 박막 간섭), post,
                         involute(순수 기어 수학), gears, harmonic, rings(허리·목 링 기어), fasteners(볼트·래치 인스턴싱),
                         fuelcell(판 97장·셀 32개), cables(배선·호스·냉각복 튜브), pilot(SkinnedMesh 동작),
                         robotcell(로봇 팔·겐트리), sockets(GLB 소켓 부착)
src/film/director.js     진행도 p → 상태 S (카메라·조명·분해·단면·래치 수·관절각·조종사 뼈·사운드 파라미터)
src/inspect/             자유 관람 모드 (카메라 조작, 선택, 2단계 분해, 단면, 측정, 조종사 표시)
src/audio/               audio.js(그래프·효과음), machine-worklet.js(액추에이터·송풍기·냉각기 합성기)
src/ui/                  loader, cursor, controls(모든 입력 컴포넌트), hud
src/viz/                 2D 공학 도표·계기 (Canvas/SVG)
src/styles/              tokens.css(디자인 토큰) + 나머지 CSS
model/build.py           Blender 5.2.1 빌드 스크립트 (`npm run model` = `.venv-blender/bin/python model/build.py`)
model/kstlib.py          bmesh·재질·소켓 도우미
model/render.py          검토 렌더 (Workbench 클레이 + Cycles 히어로)
public/assets/           kestrel.glb(슈트 + 조종사), kst_cell.glb(로봇 셀), kst_detail_*.glb(정밀 어셈블리 5종),
                         kestrel_manifest.json(부품 개수·외형 치수·재질 면적·소켓)
scripts/                 sheet.py(렌더 시트), verify(기어·소켓·수치·매니페스트 대조), render-audio(오프라인 스펙트로그램), shoot(진행도별 스크린샷)
renders/                 검토용 렌더 이미지
PLAN.md, BLENDER_METHOD.md, CONTRACT.md, CLAUDE.md, PROGRESS.md
```

## 2. 실행 환경 제약 (최종 페이지는 샌드박스 아티팩트)
- Vite로 빌드(`base: './'`)해 `dist/`를 여러 파일 아티팩트로 발행한다. 라이브러리·서체는 npm에서 번들한다.
- 페이지가 런타임에 외부 네트워크를 쓰지 않는다. 오디오·텍스처는 코드 생성, GLB는 함께 발행한 파일을 상대경로로 로드.
- Draco 압축 GLB 금지. GLB 파일당 15 MB 이하 (정밀 어셈블리·로봇 셀은 별도 파일로 필요할 때 로드).
- AudioWorklet 로드: 상대경로 → 실패 시 data: URL → 실패 시 ScriptProcessor 대체 (발행 전 실제 확인).
- `alert/confirm/prompt` 금지, localStorage에 필수 상태 저장 금지, 폼은 실제 전송하지 않는다.
- 소리는 사용자 클릭 이후에만 (ENTER HANGAR 버튼에서 오디오 초기화).
- 400px 폭(터치)부터 2560px까지, 가로 스크롤 금지. `prefers-reduced-motion`이면 정적 도면 모드.
- 60fps 목표: 픽셀 예산 DPR 상한 + 적응형 DPR, 셰이더 예열, 화면 밖 렌더 생략, 프레임마다 DOM 레이아웃 재계산 금지.
- 디버그 파라미터: `?shot=p`(결정론적 정지 프레임), `?debug`, `?q=high|low`, `?perf`(프레임 시간 기록), `?clean`(HUD 숨김).

## 3. 시각 규칙
- UI 색은 `src/tokens.css`의 토큰으로만. 시안 = 측정·계산값·치수선 전용 (측정 분포도는 시안 계열 순차 색표, 무지개 금지),
  주황 = UI에서 실제 열 전용 (연료전지 스택·배기, 응축기, 착지 직후 댐퍼 오일), 초록 = 승인, 노랑 = 토크 페인트·주의 표식.
- **3D 재질 팔레트** (PLAN 3-4): 흑연 CFRP 40~50%, 건메탈 Ti 25~32%, 백금색 6~10%, 티타늄골드 8~11%, 티타늄브론즈 1~3%, 골드 1~2%.
  - 금색 계열 합계 10~15%, **빨강 0%**. 실제 비율은 모델 매니페스트의 겉면 재질 면적으로 검사한다.
  - **금색 링 = 회전축** (관절 액추에이터 출력 링). 회전축이 아닌 곳에 금색 링을 쓰지 않는다.
  - 양극산화 색은 박막 간섭으로 만든다 (Blender Thin Film, three.js iridescence: 124 nm / 25 nm, 굴절률 2.2). 금색 도료·금색 텍스처로 흉내 내지 않는다.
  - 3D 재질 색은 UI 토큰과 별개다.
- 서체: 주석·라벨·숫자 `--f-mono`(대문자 라벨 자간 0.14em, 고정폭 숫자), 대형 글자는 핵심 계측값 1~2개에만 `--f-display`
  (장식용 대형 제목 금지), 한글 문장 `--f-body`.
- 도면 규칙 ISO 128: 외형선 실선 1.5px, 숨은선 파선, 중심선 1점쇄선, **가상선(조종사 자리) 2점쇄선**, 치수선은 가는 선 + 채운 화살촉 + 2px 틈의 보조선,
  단면 45° 해칭. 주석 9~11px. 8px 그리드 스냅. 캔버스 가는 선은 0.5px 오프셋.
- 70/30 원칙은 화면 구성에도 적용한다: 한 화면에 초점 하나, 나머지는 여백.
- 화면을 채우는 큰 제목 문구 금지. 이름·도면번호는 표제란에 작게, 시트 제목은 구석 라벨로만 (PLAN 12-5).
- 블룸은 실제 발광체(작은 상태 LED, POV HUD)에만. 눈은 빛나지 않는다. 스크린샷 검수 시 흰색 포화 픽셀 0.5% 이하.
- 단면 해칭은 재질 톤의 회색 45° (빨간 해칭 금지).

## 4. 모션 규칙
- 스프링은 `KX.spring('SERVO'|'HEAVY'|'DETENT')`, 스크럽용은 `KX.stepResponse`.
- 부품은 체결 축(래치·볼트·핀 방향)으로만 이동. 통통 튀는 만화식 이징, 무작위 흔들림, 모든 곳의 발광 금지.
- 스크롤에 묶인 것은 진행도 p(0~1)의 순수 함수. 역스크롤 시 정확히 되감긴다.
- 볼트는 십자 순서 (`S.bolt_sequence`의 12 / 8 / 6개 순서), 회전 수는 계산 시트의 `bolt_turns`.
- 착용 장면(SHEET 02)은 하중 경로 순서(발 → 머리)로 조립하고, 로봇 팔은 좌우 한 쌍씩 대칭으로 움직인다. 래치 카운터의 목표값은 매니페스트의 래치 개수.
  영화 속 착용 장면의 안무를 옮기지 않는다.
- 조종사 동작은 SkinnedMesh 뼈 회전을 p의 함수로 계산한다. 호흡·체중 이동·고개 들기 수준으로 절제하고, 얼굴 표정은 없다.
- 착지 접촉 순간 0.3초 프리즈 (`landing_freeze`).
- 자유 관람 모드(INSPECTION BAY, PLAN 5-5절): 진입 시 페이지 스크롤을 잠그고 휠은 줌으로 쓴다. EXIT/Esc로 복귀.
  도입부 점검 모드와 카메라·콜아웃·스냅 코드를 공유한다. 카메라는 스프링으로만 움직이고 바닥·슈트 내부로 들어가지 않는다.
  키보드만으로도 모든 조작이 가능해야 한다.

## 5. 숫자 규칙
- 화면의 모든 공학 숫자는 `KX.S('key')`로 읽는다. 코드에 숫자 리터럴로 공학값을 쓰지 않는다.
- **부품 개수(장갑판·내부 부품·체결 부품·래치)와 외형 치수(전고·어깨폭·깊이)는 매니페스트에서만** 읽는다. 목표값(120+, 450+, ≈700, ≈150)을 화면에 실제 개수처럼 쓰지 않는다.
- 새 숫자가 필요하면 `calc/specs.py`에 태그(spec/design/calc/const)와 함께 추가하고 재실행한다. 계산 시트를 고치면 같은 커밋에서 PLAN.md 수치도 고친다.
- 계산 시트가 자동 검사하는 설계 규칙 (실패하면 assert를 끄지 말고 설계를 고친다):
  - 액추에이터 24개 (L14 / M7 / S3), 모든 등급 토크 밀도 < 189 N·m/kg (Unitree M107)
  - 유성기어 조립 조건, 선기어·피니언 언더컷 (전위 반영), 중심거리 일치, 선기어 굽힘 안전율 ≥ 1.5
  - 허벅지 링크 안전율 ≥ 3.0, 피로한도 이하, 푸시로드 좌굴 안전율 ≥ 3.0
  - 착지 무릎 모멘트 ≤ 액추에이터 + 댐퍼, 댐퍼 압력 < 정격, 자유낙하 감지 여유 > 200 ms
  - 연료전지 모듈 부피 ≥ 기준 모듈(같은 kW/L), 전류밀도 0.3~0.8 A/cm², 시스템 효율 ≤ 스택 효율, 체결봉 하중 < 75% 보증하중
  - 중작업 + 상시 부하 ≤ 연료전지 순출력, 작동 시간 ≥ 4 h, 냉각기 COP가 카르노의 20~50%
  - 송풍기·팬의 날개/지지대 개수 서로소, HUD 지연 ≤ 20 ms, 등 모듈의 정지 상태 간섭 없음, 로봇 팔이 슈트 축에 닿음

## 6. 3D 모델 규칙 (상세는 BLENDER_METHOD.md)
- 오리지널 디자인: 영화·만화 속 슈트를 닮지 않는다. PLAN 3-7절 금지 목록(비늘 판, 입 슬릿, 빛나는 눈, 가슴 발광체·원형 동력원,
  외부 터빈, 팔뚝 공구 베이, 빨강, 전신 금색·금색 얼굴판, 외부 파우치·배관·안테나)을 지킨다.
- 세 겹 구조: 조종사 / 내부 기계층 / 외부 장갑판. 각 층을 컬렉션으로 나누고, 장갑판은 한 장씩 별도 객체 (병합 금지).
- 관절은 링(회전축) + 여유 절개 + 단일 슬라이드 캡으로만 덮는다.
- 명명: Blender Studio 규칙, 에셋 이름 `kst`. 예 `GEO-kst_thigh_link.L`, `GEO-kst_armor_chest_upper.L`, `HLP-kst_knee_pivot.L`, `MAT-kst_ti_gold`.
- 원점은 관절 회전축, 변환 적용, 부품별 사용자 속성(`part_no`, `layer`(pilot/internal/armor/cell), `material`, `mass_kg`, `explode_axis`, `explode_order`, `explode_stage`).
- 기준 재질 이름으로 만들고 웹에서 이름으로 재매핑한다.
- 반복 부품(볼트·래치·자석·연료전지 판·배터리 셀)은 Blender에서 만들지 않고 소켓만 둔다. 코드가 인스턴싱한다.
- 매니페스트 필수 항목: 층별·부위별 부품 개수, 소켓 개수·규격, 외형 치수(평가된 정점 기준), 겉면 재질 면적 비율, 삼각형 수·그리기 호출 추정.
- 목표 개수: 외부 장갑판 120장 이상, 내부 부품 450개 이상 (체결 부품 제외). 미달이면 렌더 공유 전에 보강한다.
- 조종사 피부 노출 0 (얼굴은 천 발라클라바, 손은 장갑).

## 7. 테스트
- 레퍼런스 시행착오 체크: 후처리 첫 단계 Sanitize 패스, `smoothstep(a,b,x)`는 a<b만, anisotropy 쓰는 면은 UV 필수,
  메모리 누수 방지 `dispose()`, 스크롤 정지 시 텍스트가 얼어붙지 않게 등장 애니메이션은 시간 기반.
- 모델 자동 검사 (빌드 스크립트): 조종사-슈트 간섭, 허리 ±30° 비틀기·팔 스윙·스쿼트 자세의 움직임 간섭, 가동 범위,
  매니폴드·뒤집힌 면, 소켓 규격과 계산 시트 대조, 재질 면적 비율(금색 계열 10~15%, 빨강 0).
- 헤드리스 Chromium: python3 + playwright (브라우저 `/opt/pw-browsers`). WebGL은
  `args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"]`로 실행. 화면은 맞지만 fps는 의미 없음.
- 개발 서버는 `npm run dev` (포트 5173), 빌드는 `npm run build`.
- 스크린샷은 Read 도구로 직접 보고, 콘솔 오류 0을 확인한다.
- 임시 파일은 세션 스크래치 폴더에 둔다 (저장소에 넣지 않는다).
