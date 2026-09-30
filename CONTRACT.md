# HX-01 KESTREL — 빌드 규칙 (CONTRACT)

> 코드를 쓰기 전에 읽는 규칙서. 무엇을 만드는지는 `PLAN.md`, 3D 제작 방법은 `BLENDER_METHOD.md`,
> 숫자는 `calc/specs.json`(원본 `calc/specs.py`)이 기준이다. 세 문서와 이 문서가 충돌하면
> 숫자는 계산 시트, 내용은 PLAN.md가 우선한다.
> 작업 방식: **단일 에이전트** (서브에이전트 사용 안 함).

## 1. 파일 구조 (Vite 프로젝트, 레퍼런스 OPUS MECHANICA 구조 계승 — PLAN 12절)
```
calc/specs.py            계산 시트 (실행하면 calc/specs.json과 src/specs.js를 생성)
calc/specs.json          모든 수치의 단일 원본
index.html               모든 DOM (로더, 표제란, HUD, 시트 라벨, 폼, 자유 관람 패널)
src/main.js              부트스트랩: 로더 → World 빌드 → Lenis/ScrollTrigger → 렌더 루프
src/specs.js             계산 시트 생성물 (직접 수정 금지)
src/core/                core.js(KX: specs 접근·스프링), math.js(seg/windowed/damp…), quality.js(품질 등급)
src/world/               three.js: world, environment(격납고 PMREM), materials(patchFx), post,
                         involute(순수 기어 수학), gears, harmonic, turbine, fasteners, cables, sockets(GLB 소켓 부착)
src/film/director.js     진행도 p → 상태 S (카메라·조명·분해·단면·열·사운드 파라미터)
src/inspect/             자유 관람 모드 (카메라 조작, 선택, 분해, 단면, 측정)
src/audio/               audio.js(그래프·효과음), turbine-worklet.js(터빈 합성기)
src/ui/                  loader, cursor, controls(모든 입력 컴포넌트), hud
src/viz/                 2D 공학 도표·계기 (Canvas/SVG)
src/styles/              tokens.css(디자인 토큰) + 나머지 CSS
model/build.py           Blender 빌드 스크립트 → public/assets/*.glb
scripts/                 verify(기어·소켓·수치 대조), render-audio(오프라인 스펙트로그램), shoot(진행도별 스크린샷)
renders/                 검토용 렌더 이미지
PLAN.md, BLENDER_METHOD.md, CONTRACT.md
```

## 2. 실행 환경 제약 (최종 페이지는 샌드박스 아티팩트)
- Vite로 빌드(`base: './'`)해 `dist/`를 여러 파일 아티팩트로 발행한다. 라이브러리·서체는 npm에서 번들한다.
- 페이지가 런타임에 외부 네트워크를 쓰지 않는다. 오디오·텍스처는 코드 생성, GLB는 함께 발행한 파일을 상대경로로 로드.
- Draco 압축 GLB 금지. 파일당 15 MB 이하, 전체 페이지 16 MB 이하.
- AudioWorklet 로드: 상대경로 → 실패 시 data: URL → 실패 시 ScriptProcessor 대체 (발행 전 실제 확인).
- `alert/confirm/prompt` 금지, localStorage에 필수 상태 저장 금지, 폼은 실제 전송하지 않는다.
- 소리는 사용자 클릭 이후에만 (ENTER HANGAR 버튼에서 오디오 초기화).
- 400px 폭(터치)부터 2560px까지, 가로 스크롤 금지. `prefers-reduced-motion`이면 정적 도면 모드.
- 60fps 목표: 픽셀 예산 DPR 상한 + 적응형 DPR, 셰이더 예열, 화면 밖 렌더 생략, 프레임마다 DOM 레이아웃 재계산 금지.
- 디버그 파라미터: `?shot=p`(결정론적 정지 프레임), `?debug`, `?q=high|low`, `?perf`(프레임 시간 기록), `?clean`(HUD 숨김).

## 3. 시각 규칙
- 색은 `src/tokens.css`의 토큰으로만. 시안 = 측정·계산값·치수선 전용, 주황 = UI에서 실제 열 전용,
  초록 = 승인, 노랑 = 토크 페인트. 3D 금속의 열변색 색은 재질의 물리적 색으로 토큰 규칙과 별개.
- 서체: 주석·라벨·숫자 `--f-mono`(대문자 라벨 자간 0.14em, 고정폭 숫자), 대형 글자는 핵심 계측값 1~2개에만 `--f-display` (장식용 대형 제목 금지), 한글 문장 `--f-body`.
- 도면 규칙 ISO 128: 외형선 실선 1.5px, 숨은선 파선, 중심선 1점쇄선, 치수선은 가는 선 + 채운 화살촉 + 2px 틈의 보조선,
  단면 45° 해칭. 주석 9~11px. 8px 그리드 스냅. 캔버스 가는 선은 0.5px 오프셋.
- 70/30 원칙은 화면 구성에도 적용한다: 한 화면에 초점 하나, 나머지는 여백.
- 화면을 채우는 큰 제목 문구 금지. 이름·도면번호는 표제란에 작게, 시트 제목은 구석 라벨로만 (PLAN 12-5).
- 블룸은 실제 발광체에만. 스크린샷 검수 시 흰색 포화 픽셀 0.5% 이하.
- 단면 해칭은 재질 톤의 회색 45° (빨간 해칭 금지).

## 4. 모션 규칙
- 스프링은 `KX.spring('SERVO'|'HEAVY'|'DETENT')`, 스크럽용은 `KX.stepResponse`.
- 부품은 체결 축으로만 이동. 통통 튀는 만화식 이징, 무작위 흔들림, 모든 곳의 발광 금지.
- 스크롤에 묶인 것은 진행도 p(0~1)의 순수 함수. 역스크롤 시 정확히 되감긴다.
- 볼트는 별 모양 순서(1→4→2→5→3). 회전 수는 계산 시트의 `bolt_turns`.
- 자유 관람 모드(INSPECTION BAY, PLAN 5-5절): 진입 시 페이지 스크롤을 잠그고 휠은 줌으로 쓴다. EXIT/Esc로 복귀.
  도입부 점검 모드와 카메라·콜아웃·스냅 코드를 공유한다. 카메라는 스프링으로만 움직이고 바닥·슈트 내부로 들어가지 않는다.
  키보드만으로도 모든 조작이 가능해야 한다.

## 5. 숫자 규칙
- 화면의 모든 숫자는 `KX.S('key')`로 읽는다. 코드에 숫자 리터럴로 공학값을 쓰지 않는다.
- 새 숫자가 필요하면 `calc/specs.py`에 태그(spec/design/calc/const)와 함께 추가하고 재실행한다.
- 계산 시트는 T/W ≥ 1.25, 유성기어 조립 조건, 블레이드 서로소를 자동 검사한다. 검사 실패 시 설계를 고친다.

## 6. 3D 모델 규칙 (상세는 BLENDER_METHOD.md)
- 오리지널 디자인: 영화·만화 속 기존 슈트를 닮지 않는다.
- 명명: Blender Studio 규칙, 에셋 이름 `kst`. 예 `GEO-kst_thigh_link.L`, `HLP-kst_knee_pivot.L`, `MAT-kst_ti_blast`.
- 원점은 관절 회전축, 변환 적용, 부품별 사용자 속성(`part_no`, `material`, `mass_kg`, `explode_axis`, `explode_order`).
- 기준 재질 이름으로 만들고 웹에서 이름으로 재매핑한다.
- 반복 부품은 인스턴싱. 삼각형·그리기 호출·용량 예산을 빌드 스크립트가 보고한다.
- 조종사 피부 노출 0.

## 7. 테스트
- 레퍼런스 시행착오 체크: 후처리 첫 단계 Sanitize 패스, `smoothstep(a,b,x)`는 a<b만, anisotropy 쓰는 면은 UV 필수,
  메모리 누수 방지 `dispose()`, 스크롤 정지 시 텍스트가 얼어붙지 않게 등장 애니메이션은 시간 기반.
- 헤드리스 Chromium: python3 + playwright (브라우저 `/opt/pw-browsers`). WebGL은
  `args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"]`로 실행.
- `/home/claude/kestrel`에서 `python3 -m http.server`로 서빙.
- 스크린샷은 Read 도구로 직접 보고, 콘솔 오류 0을 확인한다.
- 임시 파일은 스크래치 폴더 `/tmp/claude-0/-home-claude/fca27d38-bc7b-57b1-8a25-9c8a9b961ea9/scratchpad`.
