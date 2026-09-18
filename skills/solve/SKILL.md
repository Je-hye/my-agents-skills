---
name: solve
description: 수학 문제 이미지 또는 PDF에 손글씨 스타일 풀이를 생성할 때 사용한다. 로컬 math-handwriting-solver 프로젝트가 필요하다.
---

# /solve — 수학 손글씨 풀이 생성기

수학 문제가 담긴 이미지·PDF에 손글씨 스타일 풀이를 오버레이한다.

## 사용법

```
/solve <filepath>
```

예시:
- `/solve ~/Downloads/homework.jpg`
- `/solve problem.pdf`
- `/solve /Users/User/math/test.png`

## 지원 형식

JPG, JPEG, PNG, PDF

## 실행 방법

1. filepath가 존재하는지 확인
2. 다음 명령 실행:

```bash
cd /Users/User/src/repos/math-handwriting-solver
ANTHROPIC_API_KEY=$(security find-generic-password -a anthropic -s ANTHROPIC_API_KEY -w) \
  python -m solver "<filepath>"
```

3. 출력 파일 경로를 사용자에게 알린다
4. confidence < 80%이면 "풀이를 직접 확인하세요" 경고를 함께 표시

## 출력 파일명

`{원본파일명}_solved.{확장자}` — 원본 파일은 수정되지 않는다.
