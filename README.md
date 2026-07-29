# Moon Descent

1979년 아케이드 게임 감성으로 만든 Python/Pygame 기반의 2D 달 착륙 게임입니다.
제한된 연료로 착륙선의 자세와 속도를 제어해 표시된 착륙 지점에 안전하게
내려앉는 것이 목표입니다.

## 실행 환경

- Python 3.10 이상
- Pygame 2.5 이상

가상 환경 사용을 권장합니다.

```bash
cd lunar_lander_game
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

## 간편 실행과 배포

- **내 컴퓨터(리눅스)**: 최초 1회 `./build.sh`를 실행합니다. 이후 윈도우 키를 누르고 "Moon Descent"를 검색해 클릭하면 됩니다. 독에 고정하려면 아이콘을 우클릭하고 "즐겨찾기에 추가"를 선택하세요. 코드를 수정한 뒤에는 `./build.sh`를 다시 실행합니다.
- **다른 사람에게 공유**: `./release.sh` 한 줄로 GitHub 클라우드에서 Windows/맥/리눅스 실행 파일 3종이 빌드되어 `release/`에 저장됩니다. 각 zip/tar.gz에는 상대방용 `실행방법.txt`가 동봉됩니다. 전달 방법은 아래 "카카오톡으로 보낼 파일 고르기"를 참고하세요.
- **최초 1회 준비물**: GitHub 계정, `gh auth login` 로그인, 비공개 저장소(이미 설정되어 있음).

### 카카오톡으로 보낼 파일 고르기

`./release.sh` 실행 후 `release/` 폴더에 생기는 세 파일 중, 상대방 컴퓨터에 맞는 **하나만** 보내면 됩니다.

| 상대방 컴퓨터 | 보낼 파일 | 크기 |
|---|---|---|
| Windows (대부분의 경우) | `release/MoonDescent-windows/MoonDescent-windows.zip` | 약 15MB |
| 맥 | `release/MoonDescent-macos/MoonDescent-macos.zip` | 약 14MB |
| 리눅스 | `release/MoonDescent-linux/MoonDescent-linux.tar.gz` | 약 28MB |

상대방 OS를 모르면 Windows용을 보내는 것이 가장 확률이 높고, 가능하면 물어보고 맞는 파일을 보내세요.
세 파일 모두 안에 `실행방법.txt`가 들어 있어 받은 사람이 보안 경고 처리까지 따라 할 수 있습니다.

파일 위치: 파일 탐색기에서 `Dropbox → Personal Project → lunar_lander_game → release` 폴더를 열면 됩니다.
카카오톡 대화창에 파일을 끌어다 놓으면 전송됩니다. (Gmail 첨부는 exe가 든 zip을 차단하므로 메일 대신 카카오톡이나 Dropbox 공유 링크를 사용하세요.)

## 조작법

| 키 | 기능 |
|---|---|
| `←` / `→` | 착륙선 좌우 회전 |
| `↑` / `Space` | 주 추력기 작동 |
| `P` | 일시정지 / 계속 |
| `R` | 새 게임 |
| `Esc` | 종료 |
| `Enter` / `Space` | 시작 또는 결과 화면 넘기기 |

## 착륙 조건

착륙선 전체가 빛나는 평탄 지점 안에 있어야 하며, 다음 조건을 모두
만족해야 합니다.

- 수평 속도: 35 px/s 이하
- 하강 속도: 45 px/s 이하
- 기울기: 수직 기준 ±12° 이내

폭이 좁은 착륙 지점일수록 높은 점수 배율을 제공합니다. 안전하게 착륙하면
연료 일부를 보급받고 다음 단계로 진행합니다. 단계가 올라갈수록 중력이
증가하고 착륙 지점은 좁아집니다.

착륙선은 모든 스테이지와 재시도에서 수평·수직 속도 0으로 시작합니다.
1단계에서 추락하면 연료를 100% 보충받고,
2단계부터는 해당 단계에 처음 진입했을 때의 연료량으로 복원해 동일한 지형에서
다시 시도합니다. 화면 좌우 끝은 고전 아케이드 방식으로 서로 이어져 있습니다.
단계별 중력 증가는 실제 달의 중력 변화가 아니라 난이도 조정을 위한 게임
규칙입니다.

게임 전체에 목숨 3개가 주어지며 스테이지가 바뀌어도 다시 채워지지 않습니다.
추락할 때마다 하나씩 잃고, 세 번째 추락 시 현재 점수가 최종 점수로 확정되어
게임이 종료됩니다.

## 테스트

Pygame 창을 띄우지 않는 핵심 로직 테스트입니다.

```bash
python -m unittest discover -s tests -v
```

헤드리스 환경에서 게임 초기화까지 확인하려면 다음 명령을 사용할 수 있습니다.

```bash
SDL_VIDEODRIVER=dummy python -c "from lunar_lander.app import LunarLanderApp; app = LunarLanderApp(seed=1); app._draw()"
```
