# BuffCheck

마비노기 버프 남은 시간 알림 프로그램 (Electron + React + Python).

저장소: [ImaHost/buffcheck](https://github.com/ImaHost/buffcheck)

## 다운로드

1. [Releases](https://github.com/ImaHost/buffcheck/releases) 에서 최신 `BuffCheck-Setup-x.y.z.exe` 설치
2. 실행 후 **F8** 로 버프창 영역 지정 → 감시 시작
3. 이후 버전은 앱이 GitHub Releases를 확인해 **자동 업데이트**합니다

패치 내용은 앱의 **패치노트** 탭 또는 저장소의 [`PATCHNOTES.md`](./PATCHNOTES.md) 를 보세요.

## 개발 실행

```bash
npm install
py -m pip install -r requirements.txt
npm run build-icons-db
npm start
```

- Node.js 18+
- Python 3.10+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (개발 시 PATH 또는 기본 설치 경로)

## 배포 / 릴리스

버전을 올린 뒤 태그를 푸시하면 GitHub Actions가 Windows 설치본을 빌드하고 Release에 올립니다.

```bash
# 1) package.json version + PATCHNOTES.md 상단에 새 섹션 추가
# 2) 커밋 후 태그
git tag v1.0.0
git push origin main
git push origin v1.0.0
```

로컬에서만 설치본 만들기:

```bash
npm run dist
# 결과: release/BuffCheck-Setup-*.exe
```

## 동작 요약

1. 등록 아이콘 템플릿 매칭
2. 빨간 임박 시간 OCR로 최초 잠금 → 로컬 타이머
3. OCR과 10초 이상 차이면 재동기화
4. 설정한 임계(1초~1분) 이하만 갱신 오버레이에 표시
